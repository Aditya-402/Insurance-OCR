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

def load_questions():
    """Load questions from questions.txt"""
    try:
        with open("questions.txt", "r") as f:
            # Read as comma-separated values
            questions = [line.strip() for line in f.read().split(',') if line.strip()]
            return [f"Extract the {q} in format 'Field: Value ;; Page X'" for q in questions]
    except Exception as e:
        st.error(f"Failed to load questions: {str(e)}")
        return []

def main():
    st.title("Insurance Document OCR Processor")
    
    uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
    
    if uploaded_file is not None:
        # Save the uploaded file with original name
        original_name = uploaded_file.name
        with open(original_name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        if st.button("Process Document"):
            with st.spinner("Converting PDF to images..."):
                try:
                    output_folder, image_files = convert_pdf_to_images(original_name)
                    if not os.path.exists(output_folder):
                        st.error(f"Output folder not created: {output_folder}")
                        return
                    
                    st.session_state.output_folder = output_folder
                    st.session_state.image_files = image_files
                    st.success(f"Images saved in: {output_folder}")
                    
                    # Extract text from images
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    with st.spinner("Extracting text from images..."):
                        extracted_texts = []
                        total_images = len(st.session_state.image_files)
                        
                        for i, image_file in enumerate(st.session_state.image_files):
                            status_text.text(f"Processing page {i+1} of {total_images}")
                            progress_bar.progress((i + 1) / total_images)
                            
                            text = query_google_with_image(
                                "Extract all text from this insurance document", 
                                image_file
                            )
                            extracted_texts.append(text)
                            
                        # Save extracted texts to file
                        output_file = save_extracted_text(
                            st.session_state.output_folder, 
                            extracted_texts
                        )
                        
                        progress_bar.empty()
                        status_text.empty()
                        st.session_state.extracted_text_file = output_file
                        st.success(f"Text extraction complete! Saved to: {output_file}")
                        
                        # Query data using questions.txt
                        with st.spinner("Extracting structured data..."):
                            try:
                                questions = load_questions()
                                # Combine questions into a single prompt
                                combined_prompt = "Extract the following fields: " + ", ".join(questions)
                                
                                df, csv_path = query_gemini_with_file(
                                    st.session_state.extracted_text_file,
                                    combined_prompt # Pass the combined prompt
                                )
                                
                                if df is not None:
                                    st.session_state.csv_path = csv_path # Save path for download button
                                    st.subheader("Extracted Data")
                                    st.dataframe(df) # Display DataFrame as a table
                                    
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
                    st.error(f"Processing failed: {str(e)}")
        
        # Clean up temp file
        if os.path.exists(original_name):
            os.remove(original_name)

if __name__ == "__main__":
    main()
