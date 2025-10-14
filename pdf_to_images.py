#!/usr/bin/env python3
import os
from pdf2image import convert_from_bytes
from datetime import datetime
from typing import List, Optional, Tuple

def get_timestamp() -> str:
    return datetime.now().strftime("%H%M%S%d%m%y")

def convert_pdf_to_images(
    pdf_bytes: bytes,
    original_pdf_name: str,
    output_folder: Optional[str] = None,
    dpi: int = 300,
    fmt: str = 'png'
) -> Tuple[str, List[str]]:
    """
    Convert PDF bytes into images using high resolution (300 DPI).
    Args:
        pdf_bytes: Bytes of the PDF file.
        original_pdf_name: The original name of the PDF file, used for naming the output folder if not provided.
        output_folder: Optional. Folder to save images. If None, a new folder is created.
        dpi: Dots per inch for image conversion.
        fmt: Image format (e.g., 'png', 'jpeg').
    Returns:
        tuple: (output_folder_path, list_of_image_paths)
    """
    if output_folder is None:
        pdf_name_base = os.path.splitext(original_pdf_name)[0]
        timestamp = get_timestamp()
        output_folder = f"{pdf_name_base}_{timestamp}"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    images = convert_from_bytes(pdf_bytes, dpi=dpi)
    image_files = []
    for i, image in enumerate(images):
        output_file = os.path.join(output_folder, f'page_{i+1}.{fmt}')
        image.save(output_file, fmt.upper())
        image_files.append(output_file)
    return output_folder, image_files

if __name__ == "__main__":
    # Test with a sample PDF
    sample_pdf_path = "Maha_lakshmi.pdf"
    with open(sample_pdf_path, "rb") as f:
        pdf_bytes = f.read()
    output_folder, image_files = convert_pdf_to_images(pdf_bytes, sample_pdf_path)
    print(f"Converted images saved in: {output_folder}")
    print(f"Generated files: {image_files}")
