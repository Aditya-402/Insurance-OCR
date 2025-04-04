#!/usr/bin/env python3
import google.generativeai as genai
import time
from dotenv import load_dotenv
import os

load_dotenv()

def upload_to_gemini(path, mime_type=None):
    """
    Uploads a file to Google Cloud Gemini.
    See https://ai.google.dev/gemini-api/docs/prompting_with_media for details.
    """
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

def query_google_with_image(prompt, image_path):
    """
    Uploads the image to Gemini, starts a chat session, sends the prompt,
    and returns the extracted text.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables or .env file.")
    genai.configure(api_key=api_key) 

    generation_config = {
      "temperature": 1,
      "top_p": 0.95,
      "top_k": 40,
      "max_output_tokens": 8192,
      "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
      model_name="gemini-1.5-pro",
      generation_config=generation_config,
      system_instruction="Answer from the document; don't go beyond the context of the image.",
    )

    file = upload_to_gemini(image_path, mime_type="image/png")
    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [file],
            },
        ]
    )
    response = chat_session.send_message(prompt)
    time.sleep(5)
    return response.text

if __name__ == '__main__':
    def test_extraction():
        print("Testing Google Gemini image extraction...")
        try:
            # Example test case
            prompt = "Extract all text from this image."
            image_path = "test_image.png"  
            result = query_google_with_image(prompt, image_path)
            print("Extracted Text:")
            print(result)
        except Exception as e:
            print(f"Test failed: {str(e)}")

    test_extraction()
