import google.generativeai as genai
import os
import time
import pandas as pd

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
        model_name="gemini-1.5-pro", # Kept 1.5 Pro for potentially large text files
        generation_config=generation_config,
        system_instruction="""Answer only from the passage text provided if the value for an item is not available then provide "not in scope"

I want response in below format

<item1> : <value1> ;; <reference> ||
<item2> : <value2> ; <reference> || ....

The items list will be provided by the user
Here reference is the page number where this data is found if its on multiple pages with different values u can repeat it i mean like below

<item1> : <value1> ;; <reference1> ||
<item1> : <value2> ;; <reference2> ||
<item1> : <value3> ;; <reference3> ||

eg:
Name :  Aditya ;; page 1 ||
ID : not in scope ;; NA""",
    )

    try:
        # Read the text content from the file
        with open(filepath, 'r', encoding='utf-8') as f:
            document_text = f.read()

        # Combine the user prompt and the document text
        full_prompt = f"{user_prompt}\n\n--- Passage Text ---\n{document_text}"

        # Generate content directly
        response = model.generate_content(full_prompt)

        # Parse response into structured data
        data = []
        # Handle potential multi-line responses, split by the custom delimiter ' ||'
        lines = response.text.split(' ||')
        for line in lines:
            cleaned_line = line.strip()
            if ';;' in cleaned_line and ':' in cleaned_line:
                try:
                    field_part, page_part = cleaned_line.split(';;')
                    field, value = field_part.split(':', 1)
                    page = page_part.replace('page', '').strip()
                    data.append({
                        'Field': field.strip(),
                        'Value': value.strip(),
                        'Page': page
                    })
                except ValueError:
                    # Skip lines that don't perfectly match the expected split format after ';;'
                    print(f"Skipping malformed line: {cleaned_line}")
                    continue

        # Save to CSV in same directory as input file
        csv_path = os.path.join(os.path.dirname(filepath), 'extracted_data.csv')
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
            f.write("PolicyNumber: ABC123XYZ ;; page 1 || PatientName: John Doe ;; page 2")
        print(f"Created dummy file: {test_filepath}")

    df_result, result_csv_path = query_gemini_with_file(test_filepath, test_prompt)

    if df_result is not None:
        print("\nExtracted Data:")
        print(df_result)
        print(f"\nExtracted data saved to {result_csv_path}")
    else:
        print("\nFailed to process the document.")