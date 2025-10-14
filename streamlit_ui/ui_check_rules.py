import streamlit as st
import os
import pandas as pd
import sqlite3
import plotly.express as px
import json
from datetime import datetime
from check_rules.claims_db_creator import process_txt_file
from check_rules.config import DB_PATH, RULES_DB_PATH, PROCESSED_OUTPUT_DIR
from check_rules.rule_db_manager import get_procedure_names, get_rules_for_procedure, get_procedure_rules_expression
from check_rules.check_rule_evaluator import evaluate_submission_logic
from check_rules.l1_rule_manager import get_l1_rules_with_values_for_check_id
from check_rules.sql_tooling import check_document_submission_status, fetch_all_l2_rules_from_db
from check_rules.l2_rule_evaluator import evaluate_l2_rule_with_gemini
from streamlit_ui.html_report_generator import generate_html_report

def render_check_rules_page():
    st.header("Rule Evaluation and Database Management")



    with st.expander("Update Database from Text File", expanded=False):
        st.markdown(
            "Upload a text file (e.g., `.txt`) where each line contains `ClaimID:::Text_Content`. "
            "The text content will be processed by AI to update relevant fields in the database for the given ClaimID."
        )
        uploaded_db_file_for_update = st.file_uploader("Choose a text file to update database", type=["txt"], key="db_updater_file_top")
        if uploaded_db_file_for_update is not None:
            if st.button("Process and Update Database from File", key="update_db_button_top"):
                # Basic validation for file name
                if not uploaded_db_file_for_update.name.endswith("_output.txt"):
                    st.warning("Please select a valid '_output.txt' file for database updates.")
                else:
                    temp_db_update_dir = "temp_db_updates"
                    if not os.path.exists(temp_db_update_dir):
                        os.makedirs(temp_db_update_dir)
                    temp_file_path = os.path.join(temp_db_update_dir, uploaded_db_file_for_update.name)

                    try:
                        with open(temp_file_path, "wb") as f:
                            f.write(uploaded_db_file_for_update.getbuffer())
                        
                        with st.spinner(f"Processing '{uploaded_db_file_for_update.name}'..."):
                            try:
                                with sqlite3.connect(DB_PATH) as conn:
                                    process_txt_file(temp_file_path, conn)
                                st.success(f"Successfully processed '{uploaded_db_file_for_update.name}'.")
                            except Exception as e:
                                st.error(f"An error occurred during processing: {e}")
                    finally:
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)

    st.divider()

    st.title("Check Rules")
    st.write("Enter a Claim ID and select a procedure to see the associated rules.")

    claim_id = st.text_input("Claim ID:", placeholder="Enter Claim ID", key="claim_id_input")

    procedure_names = get_procedure_names()
    selected_procedure = st.selectbox(
        "Procedure:",
        options=procedure_names if procedure_names else ["No procedures found"],
        index=0,
        key="procedure_selectbox"
    )

    if 'fetched_rules_content_processed' not in st.session_state:
        st.session_state.fetched_rules_content_processed = []
    if 'l2_results_for_report' not in st.session_state:
        st.session_state.l2_results_for_report = []

    if st.button("Process Rules", key="process_rules_button"):
        st.session_state.fetched_rules_content_processed = []
        st.session_state.l2_results_for_report = []

        if not claim_id or not selected_procedure or selected_procedure == "No procedures found":
            st.warning("Please enter a Claim ID and select a valid procedure.")
        else:
            # --- Pre-evaluation Check ---
            with st.spinner("Performing pre-evaluation checks..."):
                expression = get_procedure_rules_expression(selected_procedure)
                # Only run logic if an expression exists for the procedure
                if expression:
                    is_passed, failed_rules = evaluate_submission_logic(expression, claim_id)
                    if not is_passed:
                        # If checks fail, display a detailed error and stop
                        st.error(f"**Pre-evaluation Failed for Claim ID {claim_id}**")
                        st.warning("The following mandatory document checks did not pass:")
                        failed_rules_formatted = "\n".join([f"- {rule}" for rule in failed_rules])
                        st.markdown(f"{failed_rules_formatted}")
                        st.stop()
                
                st.success("Pre-evaluation checks passed. Proceeding with L1 and L2 rule evaluation.")

            # --- L1 and L2 Rule Processing ---
            # This now calls the fully refactored function which handles all parsing internally.
            fetched_rules = get_rules_for_procedure(selected_procedure)

            if not fetched_rules or "No Rule IDs found" in fetched_rules[0]:
                st.warning(f"No rules found or configured for procedure: {selected_procedure}")
                st.stop()



            # --- L1 Rule Processing ---
            with st.spinner(f"Processing L1 rules for {selected_procedure}..."):
                rule_descriptions_list = get_rules_for_procedure(selected_procedure)
                processed_rules_output = []
                if not rule_descriptions_list or not rule_descriptions_list[0].startswith("CH"):
                    message = rule_descriptions_list[0] if rule_descriptions_list else f"No rules found for {selected_procedure}"
                    st.error(message)
                else:
                    for rule_entry in rule_descriptions_list:
                        try:
                            rule_id_part, question_part = rule_entry.split(": ", 1)
                            rule_id = rule_id_part.strip()
                            question = question_part.strip()
                            temp_keyword = question.lower().replace("is the ", "").replace(" submitted?", "")
                            document_keywords_to_check = [k.strip() for k in temp_keyword.split(" or ")]
                            
                            overall_submission_status = any(check_document_submission_status(claim_id, keyword) for keyword in document_keywords_to_check)
                            status_text = "Submitted: Yes" if overall_submission_status else "Submitted: No"
                            
                            rule_data = {'rule_id': rule_id, 'question': question, 'status_text': status_text, 'l1_rules': []}
                            if overall_submission_status:
                                l1_rules_with_values = get_l1_rules_with_values_for_check_id(rule_id, claim_id)
                                if l1_rules_with_values:
                                    rule_data['l1_rules'] = l1_rules_with_values
                            processed_rules_output.append(rule_data)
                        except ValueError:
                            processed_rules_output.append({'rule_id': 'Parse Error', 'question': rule_entry, 'status_text': 'Could not parse rule'})
            st.session_state.fetched_rules_content_processed = processed_rules_output

            # --- L2 Rule Processing ---
            with st.spinner("Processing L2 rules with Gemini..."):
                l2_rules = fetch_all_l2_rules_from_db(RULES_DB_PATH)
                l2_results = []
                if l2_rules:
                    for rule in l2_rules:
                        evaluation = evaluate_l2_rule_with_gemini(
                            l2_description=rule['description'],
                            l1_value=rule['l1_data_references'],
                            rules_db_path=RULES_DB_PATH,
                            claims_db_path=DB_PATH,
                            claim_id=claim_id
                        )
                        decision = 'Error'
                        if isinstance(evaluation, dict):
                            decision = evaluation.get('decision', 'Error')
                        
                        l2_results.append({
                            'rule_id': rule['rule_id'],
                            'description': rule['description'],
                            'gemini_evaluation': decision,
                            'raw_evaluation': evaluation if isinstance(evaluation, dict) else {'error': str(evaluation)}
                        })
            st.session_state.l2_results_for_report = l2_results

    # --- Display Area ---
    if st.session_state.fetched_rules_content_processed:
        st.subheader("Processed Rule Details:")
        # Display L1 Results
        for item in st.session_state.fetched_rules_content_processed:
            if 'Error' in item['rule_id']:
                 st.error(f"{item['rule_id']}: {item['question']}")
            else:
                st.markdown(f"**{item['rule_id']}**: {item['question']} - **{item['status_text']}**")
                if item.get('l1_rules'):
                    with st.container():
                        st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;*L1 Rules:*", unsafe_allow_html=True)
                        for l1_rule in item['l1_rules']:
                            desc = l1_rule.get('description', 'N/A')
                            value = l1_rule.get('value', 'N/A')
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- *{desc}* : `{value}`", unsafe_allow_html=True)
        st.markdown("--- ")

        # Display L2 Results
        if st.session_state.get('l2_results_for_report'):
            st.markdown("#### L2 Rule Evaluation Results (Powered by Gemini)")
            for result in st.session_state.l2_results_for_report:
                decision = result['gemini_evaluation']
                icon = "✅" if decision == "Pass" else "❌" if decision == "Fail" else "⚠️"
                st.markdown(f"**{icon} {result['description']}**")
                with st.expander("See Gemini's Reasoning"):
                    st.json(result['raw_evaluation'])

        # --- Charting Section ---
        valid_results = [res for res in st.session_state.fetched_rules_content_processed if 'status_text' in res]
        if valid_results:
            with st.expander("View Submission Status Summary", expanded=True):
                st.subheader("Submission Status Summary")
                status_counts = pd.Series([res['status_text'] for res in valid_results]).value_counts().reset_index()
                status_counts.columns = ['Status', 'Count']
                chart_type = st.radio("Select Chart Type:", ('Pie Chart', 'Bar Chart'), key='chart_type_selector')
                if chart_type == 'Pie Chart':
                    fig = px.pie(status_counts, names='Status', values='Count', title='Document Submission Status',
                                 color='Status', color_discrete_map={'Submitted: Yes':'green', 'Submitted: No':'red'})
                else:
                    fig = px.bar(status_counts, x='Status', y='Count', title='Document Submission Status',
                                 color='Status', color_discrete_map={'Submitted: Yes':'green', 'Submitted: No':'red'})
                st.plotly_chart(fig, use_container_width=True)

            # --- L1 Charting Section ---
            all_l1_rules = [l1_rule for item in st.session_state.fetched_rules_content_processed if item.get('l1_rules') for l1_rule in item['l1_rules']]
            if all_l1_rules:
                l1_values = []
                for rule in all_l1_rules:
                    val = rule.get('value')
                    is_valid = val is not None and str(val).strip().lower() not in ('', 'null', 'n/a') and not str(val).lower().startswith('error')
                    l1_values.append('Valid' if is_valid else 'Invalid')

                if l1_values:
                    with st.expander("View L1 Rule Value Summary", expanded=True):
                        st.subheader("L1 Rule Value Summary")
                        l1_status_counts = pd.Series(l1_values).value_counts().reset_index()
                        l1_status_counts.columns = ['Status', 'Count']
                        
                        l1_chart_type = st.radio("Select Chart Type:", ('Pie Chart', 'Bar Chart'), key='l1_chart_type_selector')
                        if l1_chart_type == 'Pie Chart':
                            fig_l1 = px.pie(l1_status_counts, names='Status', values='Count', title='L1 Rule Value Validity',
                                            color='Status', color_discrete_map={'Valid':'green', 'Invalid':'red'})
                        else:
                            fig_l1 = px.bar(l1_status_counts, x='Status', y='Count', title='L1 Rule Value Validity',
                                            color='Status', color_discrete_map={'Valid':'green', 'Invalid':'red'})
                        st.plotly_chart(fig_l1, use_container_width=True)

            # --- L2 Charting Section ---
            l2_results = st.session_state.get('l2_results_for_report', [])
            if l2_results:
                l2_decisions = [res.get('gemini_evaluation', 'Other') for res in l2_results]
                # Standardize decisions to Pass, Fail, or Other
                l2_statuses = []
                for d in l2_decisions:
                    if d == 'Pass':
                        l2_statuses.append('Pass')
                    elif d == 'Fail':
                        l2_statuses.append('Fail')
                    else:
                        l2_statuses.append('Other')

                with st.expander("View L2 Evaluation Summary", expanded=True):
                    st.subheader("L2 Evaluation Summary")
                    l2_status_counts = pd.Series(l2_statuses).value_counts().reset_index()
                    l2_status_counts.columns = ['Status', 'Count']
                    
                    l2_chart_type = st.radio("Select Chart Type:", ('Pie Chart', 'Bar Chart'), key='l2_chart_type_selector')
                    if l2_chart_type == 'Pie Chart':
                        fig_l2 = px.pie(l2_status_counts, names='Status', values='Count', title='L2 Rule Evaluation Outcome',
                                        color='Status', color_discrete_map={'Pass':'green', 'Fail':'red', 'Other':'grey'})
                    else:
                        fig_l2 = px.bar(l2_status_counts, x='Status', y='Count', title='L2 Rule Evaluation Outcome',
                                        color='Status', color_discrete_map={'Pass':'green', 'Fail':'red', 'Other':'grey'})
                    st.plotly_chart(fig_l2, use_container_width=True)

            # --- Generate Chart HTML for Report ---
            chart_html = {
                'submission_status': fig.to_html(full_html=False, include_plotlyjs='cdn'),
                'l1_values': fig_l1.to_html(full_html=False, include_plotlyjs='cdn') if 'fig_l1' in locals() else None,
                'l2_evaluation': fig_l2.to_html(full_html=False, include_plotlyjs='cdn') if 'fig_l2' in locals() else None
            }

            # --- Report Saving ---
            try:
                if not os.path.exists(PROCESSED_OUTPUT_DIR):
                    os.makedirs(PROCESSED_OUTPUT_DIR)

                # --- Save JSON Report ---
                final_json_output = {
                    "claim_id": claim_id,
                    "procedure": selected_procedure,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "l1_results": st.session_state.fetched_rules_content_processed,
                    "l2_results": st.session_state.l2_results_for_report
                }
                base_filename = f"{claim_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                json_file_path = os.path.join(PROCESSED_OUTPUT_DIR, f"{base_filename}.json")
                with open(json_file_path, 'w', encoding='utf-8') as f:
                    json.dump(final_json_output, f, indent=4)
                st.success(f"JSON report saved to {json_file_path}")

                # --- Save HTML Report ---
                html_report_path = generate_html_report(
                    claim_id=claim_id,
                    procedure=selected_procedure,
                    l1_results=st.session_state.fetched_rules_content_processed,
                    l2_results=st.session_state.l2_results_for_report,
                    charts=chart_html,
                    output_dir=PROCESSED_OUTPUT_DIR
                )
                if html_report_path.endswith('.html'):
                    st.success(f"HTML report saved to {html_report_path}")
                else: # The function returns an error string on failure
                    st.error(f"Could not save HTML report: {html_report_path}")

            except Exception as e:
                st.error(f"An error occurred during report generation: {e}")



# The main function render_check_rules_page() will be called by the main app script (main.py)
# based on sidebar navigation. Do not call it directly here.
