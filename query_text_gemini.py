import google.generativeai as genai
import os
import time
import pandas as pd
import re

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])


def query_gemini_with_file(filepath, user_prompt):
    """
    Queries Gemini with text content from a file and returns structured response.
    Assumes filepath points to a text file.
    Returns:
        tuple: (DataFrame, csv_path) or (None, None) on error
    """
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-8b", 
        generation_config=generation_config,
        system_instruction="""Provide me consolidated data from the provided prompt.
                            
                            Provided data will be in this format:

                            <item> :: <value> :: <category> ||

                            From the provided prompt check for items with not in scope, NA
                            if you find an item with NA, not in scope then see if it has valid values in any part of the document. if so then retain those lines and remove not in scopre, NA lines for that item.
                            if you find an item with NA, not in scope then see if it has no valid values in any part of the document. then retain those lines and remove not in scopre, NA lines for that item only once dont duplicate it.


                            for example
                            input:

                            === Page 1 ===
                            HospitalName :: Srikara Hospitals Miyapur :: Claim policy page 1 ||
                            HospitalLocation :: Miyapur, Hyderabad :: Claim policy page 1 ||
                            HospitalAddress :: #222 & 223, Phase 2, Mythri Nagar, Madinaguda, Miyapur, Hyderabad :: Claim policy page 1 ||
                            RohiniID :: 8900080337220 :: Claim policy page 1 ||
                            PatientName :: P MAHA LAKSHMI :: Claim policy page 1 ||
                            Gender :: Female :: Claim policy page 1 ||
                            Age :: 55 :: Claim policy page 1 ||
                            InsuredIDCard :: 13975620000016659 :: Claim policy page 1 ||
                            PolicyNumber :: P/900000/01/2023/000192 :: Claim policy page 1 ||
                            TreatingDoctor :: not in scope :: NA ||
                            NatureOfIllness :: not in scope :: NA ||
                            ProvisionalDiagnosis :: not in scope :: NA ||
                            LineofTreatment :: not in scope :: NA ||
                            RouteofDrugAdministration :: not in scope :: NA ||
                            NameofSurgery :: not in scope :: NA ||
                            DateofAdmission :: not in scope :: NA ||
                            DaysinHospital :: not in scope :: NA ||
                            EmergencyorPlanned :: not in scope :: NA ||
                            RoomType :: not in scope :: NA ||
                            PerDayRoomRent :: not in scope :: NA ||
                            AllInclusivePackageCharges :: not in scope :: NA ||
                            TotalExpectedCostofHospitalization :: not in scope :: NA ||
                            NameofTreatingDoctor :: not in scope :: NA ||
                            HospitalSeal :: not in scope :: NA ||

                            === Page 2 ===
                            HospitalName :: not in scope :: NA ||
                            HospitalLocation :: not in scope :: NA ||
                            HospitalAddress :: not in scope :: NA ||
                            RohiniID :: not in scope :: NA ||
                            PatientName :: not in scope :: NA ||
                            Gender :: not in scope :: NA ||
                            Age :: not in scope :: NA ||
                            InsuredIDCard :: not in scope :: NA ||
                            PolicyNumber :: not in scope :: NA ||
                            TreatingDoctor :: DR AKHIL DADI :: Claim policy page 2 ||
                            NatureOfIllness :: PATIENT CMAE WITH COMPLAINTS OF PAIN IN THE BOTH KNEE JOINTS SYMPTOMATICALLY STARTED SINCE 9 MONTHS - BUT AGGREVATED SINCE PAST 1 MONTH WITH H/O...SWELLING + TENDERNESS+ ROM - PAINFULL CREPITUS + :: Claim policy page 2 ||
                            ProvisionalDiagnosis :: SEVERE OA BOTH KNEES (LEFT>RIGHT) :: Claim policy page 2 ||
                            LineofTreatment :: Surgical Management :: Claim policy page 2 ||
                            RouteofDrugAdministration :: not in scope :: NA ||
                            NameofSurgery :: LEFT TOTAL KNEE REPLACEMENT SURGERY UNDER SA :: Claim policy page 2 ||
                            DateofAdmission :: not in scope :: NA ||
                            DaysinHospital :: not in scope :: NA ||
                            EmergencyorPlanned :: not in scope :: NA ||
                            RoomType :: not in scope :: NA ||
                            PerDayRoomRent :: not in scope :: NA ||
                            AllInclusivePackageCharges :: not in scope :: NA ||
                            TotalExpectedCostofHospitalization :: not in scope :: NA ||
                            NameofTreatingDoctor :: DR AKHIL DADI :: Claim policy page 2 ||
                            HospitalSeal :: not in scope :: NA ||

                            Output:

                            HospitalName :: Srikara Hospitals Miyapur :: Claim policy page 1 ||
                            HospitalLocation :: Miyapur, Hyderabad :: Claim policy page 1 ||
                            HospitalAddress :: #222 & 223, Phase 2, Mythri Nagar, Madinaguda, Miyapur, Hyderabad :: Claim policy page 1 ||
                            RohiniID :: 8900080337220 :: Claim policy page 1 ||
                            PatientName :: P MAHA LAKSHMI :: Claim policy page 1 ||
                            Gender :: Female :: Claim policy page 1 ||
                            Age :: 55 :: Claim policy page 1 ||
                            InsuredIDCard :: 13975620000016659 :: Claim policy page 1 ||
                            PolicyNumber :: P/900000/01/2023/000192 :: Claim policy page 1 ||
                            TreatingDoctor :: DR AKHIL DADI :: Claim policy page 2 ||
                            NatureOfIllness :: PATIENT CMAE WITH COMPLAINTS OF PAIN IN THE BOTH KNEE JOINTS SYMPTOMATICALLY STARTED SINCE 9 MONTHS - BUT AGGREVATED SINCE PAST 1 MONTH WITH H/O...SWELLING + TENDERNESS+ ROM - PAINFULL CREPITUS + :: Claim policy page 2 ||
                            ProvisionalDiagnosis :: SEVERE OA BOTH KNEES (LEFT>RIGHT) :: Claim policy page 2 ||
                            LineofTreatment :: Surgical Management :: Claim policy page 2 ||
                            NameofSurgery :: LEFT TOTAL KNEE REPLACEMENT SURGERY UNDER SA :: Claim policy page 2 ||
                            NameofTreatingDoctor :: DR AKHIL DADI :: Claim policy page 2 ||
                            RouteofDrugAdministration :: not in scope :: NA ||
                            DateofAdmission :: not in scope :: NA ||
                            DaysinHospital :: not in scope :: NA ||
                            EmergencyorPlanned :: not in scope :: NA ||
                            RoomType :: not in scope :: NA ||
                            PerDayRoomRent :: not in scope :: NA ||
                            AllInclusivePackageCharges :: not in scope :: NA ||
                            TotalExpectedCostofHospitalization :: not in scope :: NA ||
                            HospitalSeal :: not in scope :: NA ||""",
                        )

    try:
        # Read the text content from the file
        with open(filepath, 'r', encoding='utf-8') as f:
            document_text = f.read()

        # Combine the user prompt and the document text
        full_prompt = f"{user_prompt}\n\n--- Passage Text ---\n{document_text}"

        # Generate content directly
        response = model.generate_content(full_prompt)

        # Parse response into structured data based on prompt format: <item> :: <value> :: <category> ||
        data = []
        lines = response.text.split('||') # Split by the main delimiter
        for line in lines:
            cleaned_line = line.strip()
            if cleaned_line.count('::') == 2: # Check for exactly two '::' separators
                try:
                    item, value, category_part = [part.strip() for part in cleaned_line.split('::')]

                    # Extract page number from category_part (e.g., "Claim policy page 1")
                    page_match = re.search(r'page\s+(\d+)', category_part, re.IGNORECASE)
                    page = page_match.group(1) if page_match else 'N/A' # Default if page number not found

                    data.append({
                        'Field': item,
                        'Value': value,
                        'Category': category_part
                    })
                except ValueError:
                    # This might catch cases where split doesn't yield 3 parts
                    print(f"Skipping malformed line (unexpected split): {cleaned_line}")
                    continue
                except Exception as parse_err: # Catch other potential errors during parsing
                    print(f"Error parsing line '{cleaned_line}': {parse_err}")
                    continue
            elif cleaned_line: # Only print skip message for non-empty lines that didn't match
                 print(f"Skipping line not matching format '<item> :: <value> :: <category>': {cleaned_line}")

        # Save to CSV in same directory as input file, but with unique name
        base_filename = os.path.splitext(os.path.basename(filepath))[0]
        csv_filename = f"{base_filename}_extracted_data.csv"
        csv_path = os.path.join(os.path.dirname(filepath), csv_filename)

        df = pd.DataFrame(data)
        df.to_csv(csv_path, index=False)

        # Return the DataFrame and the CSV path
        return df, csv_path

    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return None, None
    except Exception as e:
        print(f"An error occurred during Gemini query: {e}")
        # Return None for both in case of error
        return None, None


if __name__ == "__main__":
    # Example Usage (remains mostly the same)
    test_filepath = "extracted_text.txt"  # Make sure this file exists for testing
    test_prompt = "Extract the PolicyNumber and PatientName." # Example prompt

    # Create a dummy extracted_text.txt if it doesn't exist for local testing
    if not os.path.exists(test_filepath):
        with open(test_filepath, "w") as f:
            # Using the format expected by the updated parser (from the prompt)
            f.write("PolicyNumber :: ABC123XYZ :: Claim policy page 1 || PatientName :: John Doe :: Claim policy page 2 ||")
        print(f"Created dummy file: {test_filepath}")

    df_result, result_csv_path = query_gemini_with_file(test_filepath, test_prompt)

    if df_result is not None:
        print("\nExtracted Data:")
        print(df_result)
        print(f"\nExtracted data saved to {result_csv_path}")
    else:
        print("\nFailed to process the document.")