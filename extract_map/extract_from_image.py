#!/usr/bin/env python3
from google.genai import types
import os
import mimetypes
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_gemini_client

def query_gemini_with_image(image_path, prompt_text="Fetch the text from the image"):
    """
    Uploads the image to Gemini, sends the prompt with the image,
    and returns the extracted text using the new google-genai SDK.
    """
    # Load the system instruction from the prompt file
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_file_path = os.path.join(os.path.dirname(current_script_dir), "prompts", "extract_from_image_gemini.txt")
    
    loaded_system_instruction = ""
    try:
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            loaded_system_instruction = f.read()
    except FileNotFoundError:
        error_msg = f"Prompt file not found: {prompt_file_path}. Ensure 'extract_from_image_gemini.txt' is in the 'prompts' directory."
        print(f"ERROR: {error_msg}") 
        raise FileNotFoundError(error_msg)
    except Exception as e:
        error_msg = f"Error reading prompt file {prompt_file_path}: {e}"
        print(f"ERROR: {error_msg}")
        raise Exception(error_msg)

    if not loaded_system_instruction.strip():
        error_msg = f"Loaded system instruction from {prompt_file_path} is empty. Please check the file content."
        print(f"ERROR: {error_msg}")
        raise ValueError(error_msg)

    # Initialize the client
    client = get_gemini_client()
    
    # Load the image as bytes
    with open(image_path, 'rb') as img_file:
        image_bytes = img_file.read()
    
    # Determine MIME type based on file extension
    mime_type = mimetypes.guess_type(image_path)[0] or 'image/png'
    
    # Create the content with system instruction, user prompt, and inline image data
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"{loaded_system_instruction}\n\n{prompt_text}"),
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        ),
    ]
    
    # Configure generation
    generate_content_config = types.GenerateContentConfig(
        temperature=1.0,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="text/plain",
    )
    
    # Generate content
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=contents,
        config=generate_content_config,
    )
    
    return response.text

if __name__ == '__main__':
    def test_extraction():
        print("Testing Google Gemini image extraction...")
        try:
            # Example test case
            prompt = "Extract the HospitalName and HospitalLocation."
            image_path = "test_image.png"  
            result = query_gemini_with_image(image_path, prompt_text=prompt) # Ensure args match new definition
            print("Extracted Text:")
            print(result)
        except Exception as e:
            print(f"Test failed: {str(e)}")

    test_extraction()
