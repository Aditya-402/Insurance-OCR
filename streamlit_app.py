import streamlit as st
import os
import pandas as pd
from pdf_to_images import convert_pdf_to_images
from extraction_google import query_google_with_image
from query_text_gemini import query_gemini_with_file
import sqlite3
from insu_update_db import process_txt_file, DB_PATH
from rules_agent import check_single_rule, check_rules_from_file

def save_extracted_text(output_folder, extracted_texts, base_name):
    """Save extracted texts to a file with page numbers"""
    output_file = os.path.join(output_folder, f"{base_name}.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        for i, text in enumerate(extracted_texts, 1):
            f.write(f"=== Page {i} ===\n")
            f.write(text)
            f.write("\n\n")
    return output_file

def main():
    st.set_page_config(
        page_title="Insurance Claims Reviewer Assistant", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown("<h1>Insurance Claims Reviewer Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p class='small-subtitle'>GenAI Powered</p>", unsafe_allow_html=True)

    # --- STYLING & UI --- 
    # Custom CSS for input fields to make them smaller and other style adjustments
    st.markdown("""
    <style>
        /* Targeting all text input fields */
        .stTextInput input {
            font-size: 0.9rem; /* Smaller font size */
            height: 2.5rem;    /* Reduced height */
            padding: 0.5rem;   /* Adjust padding if necessary */
        }
        /* Targeting all text area fields */
        .stTextArea textarea {
            font-size: 0.9rem; /* Smaller font size for text area */
            min-height: 50px;  /* Minimum height for text area */
        }
        /* General button styling */
        .stButton>button {
            font-size: 0.9rem;
            padding: 0.5rem 1rem;
        }
        .stDownloadButton>button {
            font-size: 0.9rem;
            padding: 0.5rem 1rem;
        }
        /* Sidebar navigation buttons */
        [data-testid="stSidebar"] .stButton button {
            width: 100%;
            text-align: left;
            margin-bottom: 5px; /* Optional: adds a bit of space between nav buttons */
        }
        h1 {
            font-size: 1.8rem; /* Slightly smaller main title */
        }
    </style>
    """, unsafe_allow_html=True)

    # Initialize current_page in session state if it doesn't exist
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Extract & Map Data" # Default page

    # Sidebar navigation with buttons
    st.sidebar.markdown("<h3 style='text-align: left;'>   </h3>", unsafe_allow_html=True)

    if st.sidebar.button("Extract & Map Data", key="btn_extract_data"):
        st.session_state.current_page = "Extract & Map Data"
    if st.sidebar.button("Check Rules", key="btn_check_rules"):
        st.session_state.current_page = "Check Rules"

    # --- Page Content based on st.session_state.current_page ---

    if st.session_state.current_page == "Extract & Map Data":
        # --- FILE UPLOAD AND PROCESSING LOGIC (TAB 1) ---
        st.header("Document Processing and Data Extraction")
        st.markdown("Upload your insurance claim document (PDF) to extract and map its data.")
        uploaded_file = st.file_uploader("Upload a PDF document", type="pdf", key="pdf_uploader_main")
        
        # Initialize session state variables for this tab
        if 'processing_complete' not in st.session_state: st.session_state.processing_complete = False
        if 'extracted_text_path' not in st.session_state: st.session_state.extracted_text_path = None
        if 'details_extracted_path' not in st.session_state: st.session_state.details_extracted_path = None
        if 'error_message' not in st.session_state: st.session_state.error_message = None
        if 'output_folder' not in st.session_state: st.session_state.output_folder = None
        if 'image_files' not in st.session_state: st.session_state.image_files = []
        if 'pdf_base_name' not in st.session_state: st.session_state.pdf_base_name = ""
        if 'last_extraction_method' not in st.session_state: st.session_state.last_extraction_method = "google"

        if uploaded_file is not None:
            temp_upload_dir = "temp_uploads"
            if not os.path.exists(temp_upload_dir):
                os.makedirs(temp_upload_dir)
            
            original_name_in_temp = os.path.join(temp_upload_dir, uploaded_file.name)
            with open(original_name_in_temp, "wb") as f:
                f.write(uploaded_file.getbuffer())

            if st.button("Process Document", key="process_doc_button"):
                st.session_state.processing_complete = False
                st.session_state.extracted_text_path = None
                st.session_state.details_extracted_path = None
                st.session_state.error_message = None
                st.session_state.pdf_base_name = os.path.splitext(uploaded_file.name)[0]
                st.session_state.output_folder = os.path.join("processed_output", st.session_state.pdf_base_name)
                st.session_state.image_files = []

                try:
                    with st.status("Converting PDF to images...", expanded=True) as status_convert:
                        if not os.path.exists(st.session_state.output_folder):
                            os.makedirs(st.session_state.output_folder)
                        _, st.session_state.image_files = convert_pdf_to_images(original_name_in_temp, output_folder=st.session_state.output_folder)
                        if not st.session_state.image_files:
                            raise ValueError("No images were generated from the PDF.")
                        status_convert.update(label=f"✅ PDF converted to {len(st.session_state.image_files)} images.", state="complete", expanded=False)
                    
                    # Placeholder for actual text extraction and data mapping logic
                    # This would involve calling your Gemini functions page by page
                    with st.status("Extracting text and mapping data...", expanded=True) as status_extract:
                        all_text = ""
                        if st.session_state.image_files:
                            with st.status("Extracting text from images...", expanded=True) as status:
                                try:
                                    total_pages = len(st.session_state.image_files)
                                    progress_bar = st.progress(0)
                                    question_file_path = "questions.txt"
                                    if not os.path.exists(question_file_path):
                                        raise FileNotFoundError(f"Required prompt file not found: {question_file_path}")
                                    with open(question_file_path, 'r', encoding='utf-8') as f:
                                        base_prompt = f.read()

                                    for idx, image_file in enumerate(st.session_state.image_files, start=1):
                                        page_status = f"Processing page {idx}/{total_pages}..."
                                        status.update(label=page_status)

                                        # Choose extraction function based on selected method
                                        if st.session_state.last_extraction_method == "google":
                                            if not os.getenv("GOOGLE_API_KEY"):
                                                raise ValueError("GOOGLE_API_KEY not found. Please set it.")
                                            extracted_text = query_google_with_image(base_prompt, image_file)
                                        else:
                                            raise ValueError(f"Unknown extraction method: {st.session_state.last_extraction_method}")

                                        if not extracted_text:
                                            extracted_text = ""

                                        page_separator = f"\n\n--- Page {idx} ---\n\n"
                                        all_text += page_separator + extracted_text
                                        progress_bar.progress(idx / total_pages)

                                    # --- Stage 2.1: Save Extracted Text ---
                                    status.update(label="Saving extracted text...")
                                    output_dir_text = st.session_state.output_folder or "output_data"
                                    os.makedirs(output_dir_text, exist_ok=True)
                                    output_text_filename = f"{os.path.splitext(original_name_in_temp)[0]}.txt"
                                    output_text_path = os.path.join(output_dir_text, output_text_filename)
                                    
                                    st.write(f"DEBUG: Attempting to write consolidated text to: {output_text_path}") # Debug Log 1
                                    
                                    with open(output_text_path, "w", encoding="utf-8") as text_file:
                                        text_file.write(all_text)
                                    
                                    st.write(f"DEBUG: Finished writing to: {output_text_path}") # Debug Log 2
                                    st.write(f"DEBUG: Does file exist after write at {output_text_path}? {os.path.exists(output_text_path)}") # Debug Log 3
                                    
                                    st.session_state.extracted_text_path = output_text_path
                                    status.update(label=f"✅ Text extraction complete! Saved to: {output_text_path}", state="complete", expanded=False)

                                except Exception as e_extract:
                                    status.update(label=f"Text Extraction Failed: {e_extract}", state="error")
                                    raise

                        # Query data using questions.txt
                        with st.spinner("Extracting structured data..."):
                            try:
                                with open(output_text_path, 'r', encoding='utf-8') as f:
                                    prompt = f.read()

                                st.write(f"DEBUG: Passing to query_gemini_with_file: {output_text_path}") # Debug Log 4
                                df, csv_path = query_gemini_with_file(
                                    output_text_path,
                                    prompt
                                )

                                if df is not None:
                                    st.subheader("Structured Data (Table):")
                                    st.dataframe(df)

                                    # --- DEBUG: Show pdf_base_name ---
                                    if 'pdf_base_name' in st.session_state:
                                        st.write(f"DEBUG: pdf_base_name = '{st.session_state.pdf_base_name}'")
                                    else:
                                        st.write("DEBUG: pdf_base_name is not in session_state here.")
                                    # --- END DEBUG ---

                                    # Offer CSV download
                                    if csv_path and os.path.exists(csv_path):
                                        with open(csv_path, "rb") as f_csv:
                                            st.download_button(
                                                label="Download data as CSV",
                                                data=f_csv.read(), # Read the content of the file for download
                                                file_name=f"{st.session_state.pdf_base_name.split('_')[0]}.csv", # Corrected download name
                                                mime="text/csv"
                                            )
                                    else:
                                        # Fallback if csv_path is not returned or file doesn't exist, but df is present
                                        csv_from_df = df.to_csv(index=False).encode('utf-8')
                                        st.download_button(
                                            label="Download data as CSV",
                                            data=csv_from_df,
                                            file_name=f"{st.session_state.pdf_base_name.split('_')[0]}.csv", # Corrected download name
                                            mime='text/csv',
                                        )
                                else:
                                    st.error("Data extraction failed or no DataFrame returned. Check logs or Gemini response.")
                            except Exception as e:
                                st.error(f"Data extraction failed: {str(e)}")
                except Exception as e:
                    st.error(f"An error occurred during processing: {e}")
                    st.session_state.error_message = str(e)
                    st.session_state.processing_complete = False

            if st.session_state.processing_complete and not st.session_state.error_message:
                if st.session_state.extracted_text_path and os.path.exists(st.session_state.extracted_text_path):
                    with open(st.session_state.extracted_text_path, 'r', encoding='utf-8') as f_text_display:
                        st.text_area("Extracted Text", f_text_display.read(), height=200, key="extracted_text_area")
                
                if st.session_state.details_extracted_path and os.path.exists(st.session_state.details_extracted_path):
                    df_display = pd.read_csv(st.session_state.details_extracted_path)
                    st.subheader("Structured Data (Table):")
                    st.dataframe(df_display)
                    
                    if 'pdf_base_name' in st.session_state and st.session_state.pdf_base_name: # Ensure base_name is not empty
                        st.write(f"DEBUG: pdf_base_name = '{st.session_state.pdf_base_name}'")
                        csv_download_filename = f"{st.session_state.pdf_base_name.split('_')[0]}.csv"
                        with open(st.session_state.details_extracted_path, "rb") as f_csv_download:
                            st.download_button(
                                label="Download data as CSV",
                                data=f_csv_download.read(),
                                file_name=csv_download_filename,
                                mime="text/csv",
                                key="download_extracted_csv"
                            )
            elif st.session_state.error_message:
                st.error(f"Processing failed: {st.session_state.error_message}")

    elif st.session_state.current_page == "Check Rules":
        st.header("Rule Evaluation and Database Management")

        # Initialize session state for rule evaluation history if it doesn't exist
        if 'rule_evaluation_history' not in st.session_state:
            st.session_state.rule_evaluation_history = []
        if 'previous_rule_evaluation_mode' not in st.session_state:
            st.session_state.previous_rule_evaluation_mode = ""

        def clear_history_on_mode_change():
            current_mode = st.session_state.get("rule_mode_radio_v2", "")
            if st.session_state.previous_rule_evaluation_mode != current_mode:
                st.session_state.rule_evaluation_history = []
                st.session_state.previous_rule_evaluation_mode = current_mode

        with st.expander("Update Database from Text File", expanded=False):
            st.markdown(
                "Upload a text file (e.g., `.txt`) where each line contains `ClaimID:::Text_Content`. "
                "The text content will be processed by AI to update relevant fields in the database for the given ClaimID."
            )
            uploaded_db_file_for_update = st.file_uploader("Choose a text file to update database", type=["txt"], key="db_updater_file_top")
            if uploaded_db_file_for_update is not None:
                if st.button("Process and Update Database from File", key="update_db_button_top"):
                    temp_db_update_dir = "temp_db_updates"
                    if not os.path.exists(temp_db_update_dir):
                        os.makedirs(temp_db_update_dir)
                    temp_file_path = os.path.join(temp_db_update_dir, uploaded_db_file_for_update.name)

                    try:
                        with open(temp_file_path, "wb") as f:
                            f.write(uploaded_db_file_for_update.getbuffer())
                        
                        conn = None
                        with st.spinner(f"Processing '{uploaded_db_file_for_update.name}' to update database..."):
                            try:
                                conn = sqlite3.connect(DB_PATH)
                                process_txt_file(temp_file_path, conn) 
                                st.success(f"Successfully processed '{uploaded_db_file_for_update.name}' and attempted to update the database.")
                            except sqlite3.Error as e:
                                st.error(f"Database error during processing '{uploaded_db_file_for_update.name}': {e}")
                            except Exception as e:
                                st.error(f"An error occurred while processing '{uploaded_db_file_for_update.name}': {e}")
                            finally:
                                if conn:
                                    conn.close()
                    except Exception as e:
                        st.error(f"An error occurred before processing could start (e.g., file saving): {e}")
                    finally:
                        if os.path.exists(temp_file_path):
                            try:
                                os.remove(temp_file_path)
                            except Exception as e_remove_db_temp:
                                st.warning(f"Could not remove temporary file {temp_file_path}: {e_remove_db_temp}")

        st.markdown("---_---") 

        st.subheader("Evaluate Rules Against the Database")
        st.markdown("Select an evaluation mode, then provide either a rule file or type a rule.")

        rule_evaluation_mode = st.radio(
            "Select Rule Evaluation Mode:",
            ("Evaluate rules for a specific Claim ID", "Evaluate rules with general queries (like chat)"),
            key="rule_mode_radio_v2",
            on_change=clear_history_on_mode_change 
        )
        if not st.session_state.previous_rule_evaluation_mode:
            st.session_state.previous_rule_evaluation_mode = rule_evaluation_mode

        claim_id_for_rules = None
        uploaded_rules_file = None
        typed_rule = ""

        if rule_evaluation_mode == "Evaluate rules for a specific Claim ID":
            claim_id_for_rules = st.text_input("Enter Claim ID to evaluate rules against:", key="claim_id_input_rules_tab")
            uploaded_rules_file = st.file_uploader("Upload a file with rules (one rule per line)", type=["txt"], key="rules_file_uploader_claim_id_mode")
            if not uploaded_rules_file:
                typed_rule = st.text_area("Or type a single rule/question to check for this Claim ID:", key="typed_rule_claim_id_mode")
        else: 
            uploaded_rules_file = st.file_uploader("Upload a file with general rules/questions (one per line)", type=["txt"], key="rules_file_uploader_general_mode")
            if not uploaded_rules_file:
                typed_rule = st.text_area("Type a single rule/question to check:", key="typed_rule_general_mode")

        if st.button("Evaluate Rules", key="eval_rules_button"):
            results_list = []
            process_for_claim_id = claim_id_for_rules if rule_evaluation_mode == "Evaluate rules for a specific Claim ID" else None
            
            if uploaded_rules_file:
                file_content = uploaded_rules_file.read().decode()
                results_list = check_rules_from_file(file_content, process_for_claim_id)
            elif typed_rule:
                result_string = check_single_rule(typed_rule, process_for_claim_id)
                results_list = [{'Rule': typed_rule, 'Result': result_string, 
                                 'ClaimID Used': process_for_claim_id if process_for_claim_id else "N/A"}]
            else:
                st.warning("Please upload a rules file or type a rule to evaluate.")

            if results_list:
                for res in results_list:
                    current_claim_id_used = res.get('ClaimID Used', process_for_claim_id if process_for_claim_id else "N/A")
                    st.session_state.rule_evaluation_history.append({
                        'Rule': res['Rule'],
                        'Result': res['Result'],
                        'ClaimID Used': current_claim_id_used
                    })
        
        if st.session_state.rule_evaluation_history:
            st.markdown("### Evaluation History")
            df_history = pd.DataFrame(st.session_state.rule_evaluation_history)
            
            if not df_history.empty and 'ClaimID Used' not in df_history.columns:
                 df_history['ClaimID Used'] = "N/A" # Ensure column exists even if all values are N/A from direct add
            elif df_history.empty:
                # Define columns for empty dataframe to prevent errors downstream
                df_history = pd.DataFrame(columns=['Rule', 'Result', 'ClaimID Used'])

            df_display = df_history.copy()
            if rule_evaluation_mode == "Evaluate rules with general queries (like chat)":
                if 'ClaimID Used' in df_display.columns:
                    df_display = df_display.drop(columns=['ClaimID Used'])
            
            st.dataframe(df_display, use_container_width=True) 

            col1, col2 = st.columns(2)
            with col1:
                if not df_history.empty:
                    csv_history = df_history.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Results as CSV",
                        data=csv_history,
                        file_name="rule_evaluation_history.csv",
                        mime="text/csv",
                        key="download_eval_history_v2"
                    )
                else:
                    st.info("No history to download.")
            with col2:
                if st.button("Clear Evaluation History", key="clear_eval_history_v2"):
                    st.session_state.rule_evaluation_history = []
                    st.rerun()

if __name__ == "__main__":
    main()
