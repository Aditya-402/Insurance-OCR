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
      system_instruction="""Instructions: Extract the following fields from the provided image, based on document categories. For each document, identify and extract the values for the listed questions. If a question’s value is not in the image, report it as "not in scope."

                            Document Fields:

                            Claim Form Page 1
                            - Hospital Name
                            - Hospital Location
                            - Hospital City
                            - Hospital Address
                            - Rohini ID
                            - Patient Name
                            - Patient Gender
                            - Patient Age
                            - Patient Insured ID Card
                            - Patient Policy Number

                            Claim Form Page 2
                            - Treating Doctor
                            - Nature Of Illness
                            - Provisional Diagnosis
                            - Line of Treatment
                            - Route of Drug Administration
                            - Name of Surgery

                            Claim Form Page 3
                            - Date of Admission
                            - Days in Hospital
                            - Emergency or Planned?
                            - Room Type
                            - Per Day Room Rent
                            - All Inclusive Package Charges
                            - Total Expected Cost of Hospitalization

                            Claim Form Page 4
                            - Name of Treating Doctor
                            - Qualification
                            - Hospital Seal

                            Assessment Record
                            - Patient Name
                            - Patient Age
                            - Treating Doctor Name or Consultant Name
                            - Complaint
                            - Diagnosis
                            - Plan
                            - Treatment
                            - Body of the page or key points from assessment or Clinical summary
                            - Date

                            Discharge Summary
                            - Patient Name
                            - Doctor Name
                            - Patient Age
                            - Patient Gender
                            - Admit Date
                            - Discharge Date
                            - Diagnosis
                            - Procedure

                            Insurance Card
                            - Policy No
                            - Customer ID Or Customer Code
                            - Member No
                            - Name of the Insured
                            - Period of Insurance from or Valid From
                            - Period of Insurance to or Valid Upto

                            Aadhaar card
                            - name
                            - gender
                            - year of birth
                            - Aadhaar number

                            Radiology Report
                            - Patient Name
                            - Doctor Name
                            - Department
                            - Patient Gender
                            - Date
                            - Patient Age
                            - Impression

                            PAN Card
                            - name
                            - pan number


                            Response Format:  
                            <item> :: <value> :: <category> ||

                            Category Determination: Identify the category based on specific text found in the image:

                            - **Claim form page 1**: if the image contains any of  
                            - "Request for Cashless Hospitalization"  
                            - "Policy Part - C"  
                            - "Rohini ID"  

                            - **Claim form page 2**: if the image contains any of  
                            - "TO BE FILLED BY TREATING DOCTOR/HOSPITAL"  
                            - "To be filled by Treating Hospital"  
                            - "To be filled by Treating Doctor"  

                            - **Assessment Record**: if the image contains any of  
                            - "Outpatient Reassessment"  
                            - "Outpatient assessment"  
                            - "Outpatient Card"  

                            - **Radiology Report**: if the image contains any of  
                            - "Xray"  
                            - "Department of radiology"  

                            - **Discharge Summary**: if the image contains  
                            - "Discharge Summary"  

                            - **Insurance Card**: if the image contains any of  
                            - "Policy Number"  
                            - "Star Health Insurance & Allied Insurance Company"  
                            - "Customer Identity Card"  

                            - **Aadhar card**: if the image contains any of  
                            - "Government of India"  
                            - "Aadhar"  
                            - "Mera Aadhar, Meri Pehchan"  

                            - **PAN Card**: if the image contains any of  
                            - "INCOME TAX DEPARTMENT"  
                            - "GOVT. OF INDIA"  
                            - "Permanent Account Number"  

                            - **Claim form page 3**: if the image contains  
                            - "DETAILS OF PATIENT ADMITTED"  

                            - **Claim form page 4**: if the image contains  
                            - "DECLARATION"  

                            - **Insurance Document**: if the image contains  
                            - "Certificate of Insurance"  

                            - **Medical Report**: if the image is identified as a medical report document  

                            - If none of the above cues are found, the category is **"Category to be determined."**

                            A document can have multiple categories; list them comma‑separated. Use "not in scope" for missing values.

                            example: 
                            if the image is detected as category Claim form page 1 then output suppose to be

                            Hospital Name :: Srikara Hospitals Miyapur :: Claim form page 1 ||
                            Hospital Location :: Mythri Nagar, Madinaguda, Miyapur, Hyderabad :: Claim form page 1 ||
                            Hospital City :: Hyderabad :: Claim form page 1 ||
                            Hospital Address :: #222 & 223, Phase 2, Mythri Nagar, Madinaguda, Miyapur, Hyderabad, :: Claim form page 1 ||
                            Rohini ID :: 8900080337220 :: Claim form page 1 ||
                            Patient Name :: P MAHA LAKSHMI :: Claim form page 1 ||
                            Patient Gender :: Female :: Claim form page 1 ||
                            Patient Age :: 55 :: Claim form page 1 ||
                            Patient Insured ID Card :: 13975620000016659 :: Claim form page 1 ||
                            Patient Policy Number :: P/900000/01/2023/000192 :: Claim form page 1 ||

                            say age detail is missing in the category detected then

                            Hospital Name :: Srikara Hospitals Miyapur :: Claim form page 1 ||
                            Hospital Location :: Mythri Nagar, Madinaguda, Miyapur, Hyderabad :: Claim form page 1 ||
                            Hospital City :: Hyderabad :: Claim form page 1 ||
                            Hospital Address :: #222 & 223, Phase 2, Mythri Nagar, Madinaguda, Miyapur, Hyderabad, :: Claim form page 1 ||
                            Rohini ID :: 8900080337220 :: Claim form page 1 ||
                            Patient Name :: P MAHA LAKSHMI :: Claim form page 1 ||
                            Patient Gender :: Female :: Claim form page 1 ||
                            Patient Age :: not in scope :: Claim form page 1 ||
                            Patient Insured ID Card :: 13975620000016659 :: Claim form page 1 ||
                            Patient Policy Number :: P/900000/01/2023/000192 :: Claim form page 1 ||

                            the same applies across other categories too.""",
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
            prompt = "Extract the HospitalName and HospitalLocation."
            image_path = "test_image.png"  
            result = query_google_with_image(prompt, image_path)
            print("Extracted Text:")
            print(result)
        except Exception as e:
            print(f"Test failed: {str(e)}")

    test_extraction()
