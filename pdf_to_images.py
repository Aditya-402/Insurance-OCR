#!/usr/bin/env python3
import os
from pdf2image import convert_from_path
from datetime import datetime

def get_timestamp():
    return datetime.now().strftime("%M%H%d%m%y")

def convert_pdf_to_images(pdf_path, output_folder=None, dpi=300, fmt='png'):
    """
    Convert a PDF file into images using high resolution (300 DPI).
    Returns:
        tuple: (output_folder_path, list_of_image_paths)
    """
    if output_folder is None:
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        timestamp = get_timestamp()
        output_folder = f"{pdf_name}_{timestamp}"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    images = convert_from_path(pdf_path, dpi=dpi)
    image_files = []
    for i, image in enumerate(images):
        output_file = os.path.join(output_folder, f'page_{i+1}.{fmt}')
        image.save(output_file, fmt.upper())
        image_files.append(output_file)
    return output_folder, image_files

if __name__ == "__main__":
    # Test with a sample PDF
    sample_pdf_path = "Maha_lakshmi.pdf"
    output_folder, image_files = convert_pdf_to_images(sample_pdf_path)
    print(f"Converted images saved in: {output_folder}")
    print(f"Generated files: {image_files}")
