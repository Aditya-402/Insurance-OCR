import streamlit as st
import os
import pandas as pd
from pdf_to_images import convert_pdf_to_images
from extraction_google import query_google_with_image
from query_text_gemini import query_gemini_with_file

def save_extracted_text(output_folder, extracted_texts):
    """Save extracted texts to a file with page numbers"""
    output_file = os.path.join(output_folder, "extracted_text.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        for i, text in enumerate(extracted_texts, 1):
            f.write(f"=== Page {i} ===\n")
            f.write(text)
            f.write("\n\n")
    return output_file

def main():
    st.title("Insurance Document OCR Processor")
    
    uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
    
    if uploaded_file is not None:
        # Save the uploaded file with original name
        original_name = uploaded_file.name
        with open(original_name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        if st.button("Process Document"):
            st.session_state.processing_complete = False
            st.session_state.extracted_text_path = None
            st.session_state.details_extracted_path = None
            st.session_state.error_message = None
            st.session_state.last_extraction_method = "google" # Default extraction method
            st.session_state.output_folder = None # Initialize output folder state
            st.session_state.image_files = [] # Initialize image files state

            try:
                # --- Stage 1: PDF to Images --- Wrap in st.status
                output_folder = None
                image_files = []
                with st.status("Converting PDF to images...", expanded=True) as status:
                    try:
                        output_folder, image_files = convert_pdf_to_images(original_name)
                        if not image_files:
                             raise ValueError("No images were generated from the PDF.")

                        st.session_state.output_folder = output_folder
                        st.session_state.image_files = image_files
                        status.update(label=f"✅ PDF converted to {len(image_files)} images in: {output_folder}", state="complete", expanded=False)
                    except Exception as e_convert:
                        status.update(label=f"PDF Conversion Failed: {e_convert}", state="error")
                        raise # Re-raise the exception to stop processing

                # --- Stage 2: Image to Text (Page by Page) --- Wrap in st.status
                all_text = ""
                if st.session_state.image_files: # Proceed only if images were created
                    with st.status("Extracting text from images...", expanded=True) as status:
                        try:
                            total_pages = len(st.session_state.image_files)
                            progress_bar = st.progress(0)
                            question_file_path = "questions.txt" # Consider making this configurable
                            if not os.path.exists(question_file_path):
                                raise FileNotFoundError(f"Required prompt file not found: {question_file_path}")
                            with open(question_file_path, 'r', encoding='utf-8') as f:
                                base_prompt = f.read()

                            for idx, image_file in enumerate(st.session_state.image_files, start=1):
                                page_status = f"Processing page {idx}/{total_pages}..."
                                status.update(label=page_status) # Update status label

                                # Choose extraction function based on selected method
                                if st.session_state.last_extraction_method == "google":
                                    # Ensure API key is available for Google
                                    if not os.getenv("GOOGLE_API_KEY"):
                                         raise ValueError("GOOGLE_API_KEY not found. Please set it.")
                                    extracted_text = query_google_with_image(base_prompt, image_file)
                                else:
                                    raise ValueError(f"Unknown extraction method: {st.session_state.last_extraction_method}")

                                if not extracted_text:
                                     extracted_text = "" # Ensure it's a string

                                page_separator = f"\n\n--- Page {idx} ---\n\n"
                                all_text += page_separator + extracted_text
                                progress_bar.progress(idx / total_pages)

                            # --- Stage 2.1: Save Extracted Text ---
                            status.update(label="Saving extracted text...")
                            output_dir_text = st.session_state.output_folder or "output_data" # Use image folder or fallback
                            os.makedirs(output_dir_text, exist_ok=True)
                            output_text_filename = f"{os.path.splitext(original_name)[0]}_extracted.txt"
                            output_text_path = os.path.join(output_dir_text, output_text_filename)
                            with open(output_text_path, "w", encoding="utf-8") as text_file:
                                text_file.write(all_text)

                            st.session_state.extracted_text_path = output_text_path
                            status.update(label=f"✅ Text extraction complete! Saved to: {output_text_path}", state="complete", expanded=False)

                        except Exception as e_extract:
                            status.update(label=f"Text Extraction Failed: {e_extract}", state="error")
                            raise # Re-raise to stop processing

                # --- Post Extraction --- (Outside status blocks)
                # Mark overall processing as complete (for enabling next step button)
                st.session_state.processing_complete = True
                st.session_state.error_message = None

                # Query data using questions.txt
                with st.spinner("Extracting structured data..."):
                    try:
                        with open(output_text_path, 'r', encoding='utf-8') as f:
                            prompt = f.read()
                        
                        df, csv_path = query_gemini_with_file(
                            output_text_path,
                            prompt
                        )
                        
                        if df is not None:
                            st.session_state.csv_path = csv_path # Save path for download button
                            st.subheader("Extracted Data")
                            # st.dataframe(df) # Display DataFrame as a table - Replaced
                            st.data_editor(df) # Use data_editor for interactivity

                            # Show CSV download button
                            with open(csv_path, "rb") as f:
                                st.download_button(
                                    label="Download CSV",
                                    data=f,
                                    file_name="extracted_data.csv",
                                    mime="text/csv"
                                )
                        else:
                            st.error("Data extraction failed. Check logs or Gemini response.")
                            
                    except Exception as e:
                        st.error(f"Data extraction failed: {str(e)}")
            except Exception as e:
                # Catch errors raised from status blocks or other issues
                st.error(f"An error occurred during processing: {e}")
                st.session_state.error_message = str(e)
                st.session_state.processing_complete = False

        # Clean up temp file
        if os.path.exists(original_name):
            os.remove(original_name)

if __name__ == "__main__":
    main()
