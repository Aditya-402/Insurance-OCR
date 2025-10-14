import streamlit as st
import os

from datetime import datetime
from pdf_to_images import convert_pdf_to_images
from extract_map.extract_from_image import query_gemini_with_image
from extract_map.text_consolidation import parse_and_split_file, consolidate_and_output

def render_extract_map_page():
    st.header("Document Processing and Data Extraction")
    st.markdown("Upload your insurance claim document (PDF) to extract and map its data.")
    uploaded_file = st.file_uploader("Upload a PDF document", type="pdf", key="pdf_uploader_main")
    
        # Initialize session state variables for this tab
    default_session_states = {
        'processing_complete': False,
        'extracted_text_path': None,
        'details_extracted_path': None,
        'error_message': None,
        'output_folder': None,
        'image_files': [],
        'pdf_base_name': "",
        'last_extraction_method': "google",
        'part1_file_path': None,
        'part2_file_path': None,
        'processed_output_file_path': None
    }
    for key, value in default_session_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if uploaded_file is not None:

        if st.button("Process Document", key="process_doc_button"):
            # Reset session state for a new run, using the defaults defined above
            for key in default_session_states:
                if key != 'last_extraction_method':  # Don't reset the method
                    st.session_state[key] = default_session_states[key]

            st.session_state.pdf_base_name = os.path.splitext(uploaded_file.name)[0]
            current_time_str = datetime.now().strftime("%H%M%S_%d%m%y")
            st.session_state.output_folder = os.path.join("processed_output", f"{st.session_state.pdf_base_name}_{current_time_str}")

            try:
                with st.status("Converting PDF to images...", expanded=True) as status_convert:
                    os.makedirs(st.session_state.output_folder, exist_ok=True)
                    _, st.session_state.image_files = convert_pdf_to_images(
                        pdf_bytes=uploaded_file.getbuffer(), 
                        original_pdf_name=uploaded_file.name, 
                        output_folder=st.session_state.output_folder
                    )
                    if not st.session_state.image_files:
                        raise ValueError("No images were generated from the PDF.")
                    status_convert.update(label=f"✅ PDF converted to {len(st.session_state.image_files)} images.", state="complete", expanded=False)
                
                with st.status("Extracting text and mapping data...", expanded=True) as status_extract:
                    all_text = ""
                    if st.session_state.image_files:
                        try:
                            total_pages = len(st.session_state.image_files)
                            progress_bar = st.progress(0)
                            for idx, image_file in enumerate(st.session_state.image_files, start=1):
                                page_status = f"Extracting text from image {idx}/{total_pages}..."
                                status_extract.update(label=page_status)

                                if not os.getenv("GOOGLE_API_KEY"):
                                    raise ValueError("GOOGLE_API_KEY not found. Please set it.")
                                extracted_text = query_gemini_with_image(image_file)

                                if not extracted_text:
                                    extracted_text = ""

                                page_separator = f"\n\n--- Page {idx} ---\n\n"
                                all_text += page_separator + extracted_text
                                progress_bar.progress(idx / total_pages)

                            status_extract.update(label="Saving extracted text...")
                            output_dir_text = st.session_state.output_folder
                            os.makedirs(output_dir_text, exist_ok=True)
                            output_text_filename = f"{st.session_state.pdf_base_name}.txt"
                            output_text_path = os.path.join(output_dir_text, output_text_filename)
                            
                            with open(output_text_path, "w", encoding="utf-8") as text_file:
                                text_file.write(all_text)
                            
                            status_extract.update(label="Splitting document into parts (document_processor)..." )
                            try:
                                os.makedirs(st.session_state.output_folder, exist_ok=True)
                                part1_target_path = os.path.join(st.session_state.output_folder, f"{st.session_state.pdf_base_name}_part1.txt")
                                part2_target_path = os.path.join(st.session_state.output_folder, f"{st.session_state.pdf_base_name}_part2.txt")

                                returned_part1_path, returned_part2_path = parse_and_split_file(
                                    input_path=output_text_path,
                                    part1_path=part1_target_path,
                                    part2_path=part2_target_path
                                )
                                st.session_state.part1_file_path = returned_part1_path 
                                st.session_state.part2_file_path = returned_part2_path

                                if not (st.session_state.part1_file_path and os.path.exists(st.session_state.part1_file_path) and 
                                        st.session_state.part2_file_path and os.path.exists(st.session_state.part2_file_path)):
                                    raise FileNotFoundError("Part1 or Part2 file was not created successfully by parse_and_split_file.")

                                status_extract.update(label="Consolidating processed parts (document_processor)..." )
                                base_filename_for_consolidate = os.path.join(st.session_state.output_folder, st.session_state.pdf_base_name)
                                consolidate_and_output(base_filename_for_consolidate) 

                                st.session_state.processed_output_file_path = os.path.join(st.session_state.output_folder, f"{st.session_state.pdf_base_name}_output.txt")

                            except Exception as e_doc_proc:
                                st.session_state.error_message = f"Document Sub-Processing (document_processor) Failed: {e_doc_proc}"
                                status_extract.update(label=st.session_state.error_message, state="error")
                                st.error(st.session_state.error_message)
                                
                            st.session_state.extracted_text_path = output_text_path

                        except Exception as e_extract:
                            status_extract.update(label=f"Text Extraction Failed: {e_extract}", state="error")
                            raise

                    st.session_state.processing_complete = True
                    # If an error occurred in the sub-processing, mark completion as False.
                    if st.session_state.error_message and "Document Sub-Processing (document_processor) Failed" in st.session_state.error_message:
                        st.session_state.processing_complete = False
                status_extract.update(label="✅ Processing complete!", state="complete", expanded=False)

            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
                st.session_state.error_message = str(e)
                st.session_state.processing_complete = False


# The main function render_extract_map_page() will be called by the main app script (main.py)
# based on sidebar navigation. Do not call it directly here.
