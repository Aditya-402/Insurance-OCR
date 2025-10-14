import os
import shutil
import pytest
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image

# Add the project root to the Python path to allow importing the script
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pdf_to_images import convert_pdf_to_images

@pytest.fixture(scope="module")
def dummy_pdf_bytes():
    """Creates a dummy two-page PDF in memory and returns its bytes."""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Page 1
    p.drawString(100, 750, "This is the first page.")
    p.showPage()
    
    # Page 2
    p.drawString(100, 750, "This is the second page.")
    p.showPage()
    
    p.save()
    buffer.seek(0)
    return buffer.read()

def test_conversion_with_auto_folder(dummy_pdf_bytes):
    """Tests PDF conversion where the output folder is created automatically."""
    original_name = "test_doc.pdf"
    output_folder, image_files = convert_pdf_to_images(dummy_pdf_bytes, original_name)
    
    try:
        # 1. Check if the folder was created
        assert os.path.isdir(output_folder)
        assert original_name.split('.')[0] in output_folder

        # 2. Check if the correct number of images were created
        assert len(image_files) == 2
        assert os.path.exists(image_files[0])
        assert os.path.exists(image_files[1])

        # 3. Check if the files are valid images
        with Image.open(image_files[0]) as img:
            assert img.format.lower() == 'png'
    finally:
        # 4. Clean up the created folder
        if os.path.isdir(output_folder):
            shutil.rmtree(output_folder)

def test_conversion_with_specified_folder(dummy_pdf_bytes):
    """Tests PDF conversion with a pre-specified output folder."""
    output_folder = "temp_test_output"
    original_name = "another_doc.pdf"

    # Ensure the folder doesn't exist before the test
    if os.path.isdir(output_folder):
        shutil.rmtree(output_folder)

    returned_folder, image_files = convert_pdf_to_images(
        dummy_pdf_bytes, original_name, output_folder=output_folder
    )

    try:
        # 1. Check that the specified folder was used
        assert returned_folder == output_folder
        assert os.path.isdir(output_folder)
        assert len(os.listdir(output_folder)) == 2
    finally:
        # 2. Clean up
        if os.path.isdir(output_folder):
            shutil.rmtree(output_folder)

def test_conversion_with_jpeg_format(dummy_pdf_bytes):
    """Tests that the image format can be changed to JPEG."""
    original_name = "jpeg_test.pdf"
    output_folder, image_files = convert_pdf_to_images(
        dummy_pdf_bytes, original_name, fmt='jpeg'
    )

    try:
        assert image_files[0].endswith('.jpeg')
        with Image.open(image_files[0]) as img:
            assert img.format.lower() == 'jpeg'
    finally:
        if os.path.isdir(output_folder):
            shutil.rmtree(output_folder)
