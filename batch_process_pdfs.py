import os
import argparse
import logging
from datetime import datetime
from tqdm import tqdm
import pandas as pd
from pdf_to_images import convert_pdf_to_images
from extraction_google import query_google_with_image
from query_text_gemini import query_gemini_with_file


def setup_logging(log_path):
    logging.basicConfig(
        filename=log_path,
        filemode='w',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def process_pdf(pdf_path, output_folder, questions_file):
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    try:
        # 1. Convert PDF to images
        images_folder, image_files = convert_pdf_to_images(pdf_path)
        if not image_files:
            raise RuntimeError(f"No images generated from PDF: {pdf_path}")

        # 2. Extract text from images
        all_text = ""
        with open(questions_file, 'r', encoding='utf-8') as f:
            base_prompt = f.read()
        for idx, image_file in enumerate(image_files, start=1):
            extracted_text = query_google_with_image(base_prompt, image_file)
            page_separator = f"\n\n--- Page {idx} ---\n\n"
            all_text += page_separator + (extracted_text or "")

        # 3. Save extracted text
        output_text_path = os.path.join(output_folder, f"{pdf_name}_extracted.txt")
        with open(output_text_path, "w", encoding="utf-8") as text_file:
            text_file.write(all_text)

        # 4. Query Gemini for structured data
        df, csv_path = query_gemini_with_file(output_text_path, all_text)
        if df is not None:
            csv_out_path = os.path.join(output_folder, f"{pdf_name}_extracted.csv")
            df.to_csv(csv_out_path, index=False)
            logging.info(f"SUCCESS: {pdf_path} -> {csv_out_path}")
        else:
            logging.error(f"FAIL: {pdf_path} - Gemini extraction returned None")
    except Exception as e:
        logging.error(f"FAIL: {pdf_path} - {e}")


def main():
    parser = argparse.ArgumentParser(description="Batch process PDFs for OCR and Gemini extraction.")
    parser.add_argument('input_folder', help='Folder containing PDF files to process')
    parser.add_argument('--questions', default='questions.txt', help='Path to questions.txt file')
    args = parser.parse_args()

    now = datetime.now().strftime('%H%M%S_%d%m%y')
    output_folder = f"batch_process_{now}"
    os.makedirs(output_folder, exist_ok=True)
    log_path = os.path.join(output_folder, "batch_process.log")
    setup_logging(log_path)

    pdf_files = [f for f in os.listdir(args.input_folder) if f.lower().endswith('.pdf')]
    if not pdf_files:
        logging.error(f"No PDF files found in {args.input_folder}")
        return

    logging.info(f"Processing {len(pdf_files)} PDF(s) in '{args.input_folder}'. Output to '{output_folder}'.")
    for pdf_file in tqdm(pdf_files, desc="Processing PDFs", file=sys.__stdout__):
        pdf_path = os.path.join(args.input_folder, pdf_file)
        logging.info(f"Starting: {pdf_path}")
        process_pdf(pdf_path, output_folder, args.questions)
    logging.info(f"Batch processing complete. See log: {log_path}")

import sys
from contextlib import contextmanager

@contextmanager
def redirect_stdout_stderr_to_logger():
    class StreamToLogger:
        def __init__(self, level):
            self.level = level
            self.linebuf = ''
        def write(self, buf):
            for line in buf.rstrip().splitlines():
                logging.log(self.level, line.rstrip())
        def flush(self):
            pass
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StreamToLogger(logging.INFO)
    sys.stderr = StreamToLogger(logging.ERROR)
    try:
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

if __name__ == "__main__":
    with redirect_stdout_stderr_to_logger():
        main()
