# Insurance OCR Project

This project uses Streamlit and Google Gemini to extract structured data from insurance document PDFs.

## Features

*   Upload PDF insurance documents.
*   Convert PDF pages to images.
*   Extract text from images using Google's Gemini vision capabilities (via `extraction_google.py` - though this seems less used now).
*   Extract structured key-value pairs from the combined text of the PDF using Google Gemini (`query_text_gemini.py`).
*   Display extracted data in a table format.
*   Download extracted data as a CSV file.
*   **Batch processing:** Use `batch_process_pdfs.py` to process all PDFs in a folder via the same pipeline, with progress tracked by `tqdm` and detailed logs saved per batch.

## Recent Updates (April 2025)

- **Stepwise UI Feedback:** The app now uses Streamlit's `st.status` to show clear progress for each processing step (PDF → images, image → text, text → structured data). Success ticks appear for each completed stage.
- **Interactive Table Filtering:** The extracted data table now uses `st.data_editor`, allowing you to filter and sort by Field, Value, and Page directly in the UI.
- **Cleaner UI:** The extraction log and raw text preview have been removed for a more streamlined experience.
- **Bug Fixes & Refactoring:** Improved error handling and code organization.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Aditya-402/Insurance-OCR.git
    cd Insurance-OCR
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt 
    ```
    *(Note: We need to create a `requirements.txt` file)*

4.  **Set up environment variables:**
    *   Create a file named `.env` in the project root directory.
    *   Add your Google API key to the `.env` file:
        ```
        GOOGLE_API_KEY='YOUR_GOOGLE_API_KEY'
        ```
    *   *(Optional: If using Google Cloud Vision directly via a service account)* Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of your service account key JSON file. This doesn't seem to be the primary method used currently.

## Usage

1.  **Run the Streamlit app:**
    ```bash
    conda activate insurance_ocr_env
    streamlit run streamlit_app.py
    ```

2.  **Open your web browser** to the URL provided by Streamlit (usually `http://localhost:8501`).

3.  **Upload a PDF** file using the file uploader.

4.  The app will process the PDF, extract text, query Gemini for structured data based on `questions.txt`, display the results in a filterable table, and provide a button to download the data as a CSV.

## Security Note
- **Never commit your `.env` file** to version control. It should be listed in `.gitignore` by default. Use `.env.example` for reference.

## Files

*   `streamlit_app.py`: The main Streamlit application file.
*   `pdf_to_images.py`: Handles conversion of PDF pages to images.
*   `extraction_google.py`: Contains functions for text extraction from images using Google AI (potentially legacy or alternative method).
*   `query_text_gemini.py`: Queries the Gemini model with extracted text to get structured data.
*   `questions.txt`: List of fields to extract from the documents.
*   `.env.example`: Example environment file (requires user to create `.env`).
*   `.gitignore`: Specifies intentionally untracked files that Git should ignore.
*   `requirements.txt`: Lists Python package dependencies (to be created).
*   `README.md`: This file.
