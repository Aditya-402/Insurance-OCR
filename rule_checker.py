import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

with open(r'C:\Users\ADMIN\OneDrive\Project-2025\Insurance_ocr\patient1_205814090425\patient1_extracted.txt', 'r', encoding='utf-8') as f:
    document_text = f.read()


model = genai.GenerativeModel(
  model_name="gemini-1.5-flash-8b",
  generation_config=generation_config,  
)

rules = ["Claim Form, Assessment Record, X-Ray, Insurance Card, Aadhar, Pan card", 
         "Claim Form, Assessment Record, Discharge, X-Ray, Insurance Card, Aadhar, Pan card"
        ]

for rule in rules:
    chat_session = model.start_chat(
  history=[]
)
    response = chat_session.send_message(f"""I want you to check in the below \n\n {document_text} do we have \n\n{rule}\n\n\ni just want output to be like below\n\nClaim form : yes ....""")
    print(response.text)
    print("****************************************")