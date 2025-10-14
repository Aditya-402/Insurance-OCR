import os
import re
import logging
import json
from typing import Union

try:
    from .config import get_gemini_model
except ImportError:
    from config import get_gemini_model

# Configure logging
logging.basicConfig(level=logging.INFO)


try:
    # For when imported as part of a package
    from .sql_tooling import _fetch_data_for_l1_rule
except ImportError:
    # For when run as a standalone script
    from sql_tooling import _fetch_data_for_l1_rule

def evaluate_l2_rule_with_gemini(l2_description: str, l1_value: str, rules_db_path: str, claims_db_path: str, claim_id: str) -> Union[dict, str]:
    """
    Evaluates an L2 rule using the Gemini Developer API.
    
    For complex rules, it fetches underlying L1 data, constructs a detailed prompt,
    and expects a structured JSON response. For simple rules, it uses a basic prompt.
    
    Returns a dictionary with evaluation details or an error string.
    """


    prompt = ""
    # Check if l1_value contains rule IDs to be dereferenced
    # Check for keywords that imply a complex comparison rule.
    complex_keywords = ['same', 'match', 'compare', 'verify', 'check if']
    if any(keyword in l2_description.lower() for keyword in complex_keywords):
        try:
            rule_pairs = [pair.strip().split(':', 1) for pair in l1_value.split(',')]
            if not rule_pairs or len(rule_pairs[0]) < 2:
                return {"decision": "Cannot Determine", "reasoning": f"Invalid L1 data format: {l1_value}"}

            # Fetch all data, preserving order
            ordered_fetched_data = [{'document': p[0].strip(), 'value': _fetch_data_for_l1_rule(p[1].strip(), rules_db_path, claims_db_path, claim_id)} for p in rule_pairs]

            primary_source = ordered_fetched_data[0]
            secondary_sources = ordered_fetched_data[1:]

            primary_data_str = f"- {primary_source['document']}: {primary_source['value']}"
            secondary_data_str = "\n".join([f"- {s['document']}: {s['value']}" for s in secondary_sources])

            # Load the prompt from the external file
            try:
                prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'gemini_2-5f_l2_evaluation_prompt.txt')
                with open(prompt_path, 'r') as f:
                    prompt_template = f.read()
            except FileNotFoundError:
                logging.error(f"Prompt file not found at {prompt_path}")
                return "Error: Prompt template file not found."

            # Format the prompt with the required data
            prompt = prompt_template.format(
                l2_description=l2_description,
                primary_source_id=primary_source['document'],
                primary_data=primary_source['value'],
                secondary_data_formatted=secondary_data_str
            )

        except Exception as e:
            logging.error(f"Error processing L1 rule IDs for L2 prompt: {e}")
            return f"Error: {e}"
    else:
        # Fallback to old behavior for simple values
        prompt = (
            f'Rule: \"{l2_description}\"\n'
            f'Data: \"{l1_value}\"\n\n'
            'Based on the provided data, does it satisfy the rule? '
            'Please answer with only \"Pass\", \"Fail\", or \"Cannot Determine\". Do not add any explanation.'
        )

    try:
        # Determine the required response type
        response_mime_type = "application/json" if "JSON" in prompt else "text/plain"
        
        # Get the configured model from the centralized config
        result = get_gemini_model(response_mime_type=response_mime_type)
        if not result:
            return "Error: Gemini model could not be initialized. Check API_KEY."
            
        # Unpack the client, model name, and config
        client, model_name, config = result
        
        # Generate content using the new client format
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config
        )
        
        # If we expect JSON, try to parse it
        if "JSON Response" in prompt:
            try:
                cleaned_text = response.text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:].strip()
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3].strip()
                
                result_json = json.loads(cleaned_text)
                
                if all(k in result_json for k in ['primary_source', 'comparisons', 'overall_decision', 'overall_reasoning']):
                    return result_json
                else:
                    logging.warning(f"Gemini returned incomplete JSON: {result_json}. Defaulting.")
                    return {"decision": "Cannot Determine", "reasoning": f"Incomplete JSON response from model: {result_json}"}
            except (json.JSONDecodeError, TypeError) as e:
                logging.warning(f"Failed to parse Gemini JSON response: '{response.text}'. Error: {e}. Defaulting.")
                return {"decision": "Cannot Determine", "reasoning": f"Model returned non-JSON response: {response.text}"}
        else:
            # Handle simple Pass/Fail response
            cleaned_response = response.text.strip().replace('.', '')
            if cleaned_response in ["Pass", "Fail", "Cannot Determine"]:
                return {"decision": cleaned_response, "reasoning": "Simple evaluation."}
            else:
                logging.warning(f"Gemini returned an unexpected response: '{response.text}'. Defaulting.")
                raw_response = response.text
                match = re.search(r'"overall_decision"\s*:\s*\"(Pass|Fail)\"', raw_response, re.IGNORECASE)
                if match:
                    return {"decision": match.group(1), "reasoning": f"Recovered from malformed JSON: {raw_response}"}
                else:
                    return {
                        "decision": "Cannot Determine",
                        "reasoning": f"Unexpected response from model: {raw_response}"
                    }

    except Exception as e:
        logging.error(f"Error calling Gemini API: {e}")
        raw_response = str(e)
        match = re.search(r'"overall_decision"\s*:\s*\"(Pass|Fail)\"', raw_response, re.IGNORECASE)
        if match:
            return {"decision": match.group(1), "reasoning": f"Recovered from malformed JSON: {raw_response}"}
        else:
            return {
                "decision": "Cannot Determine",
                "reasoning": f"Unexpected response from model: {raw_response}"
            }

if __name__ == '__main__':
    # This block is for standalone testing of the Gemini tooling.
    from config import DB_PATH, RULES_DB_PATH

    try:
        # Example of a complex rule evaluation
        test_l2_description = "Check if the Patient Name is the same in the Claim Form and the Aadhaar card, PAN card, Assessment Record, Discharge Summary, and Radiology Report"
        test_l1_value = "Claim form : L1_01_06, Aadhar card : L1_05_01, Pan Card : L1_07_01, Assessment Record : L1_02_01, Discharge Summary : L1_03_01, Radiology Report : L1_06_01"
        test_claim_id = "8956"  # Use a valid claim_id from your test database

        print(f"--- Running Standalone Test for Gemini L2 Evaluation ---")
        print(f"Claim ID: {test_claim_id}")
        print(f"L2 Rule: '{test_l2_description}'")
        print(f"L1 Data References: '{test_l1_value}'")
        print("----------------------------------------------------------")

        evaluation_result = evaluate_l2_rule_with_gemini(
            test_l2_description, 
            test_l1_value,
            RULES_DB_PATH,
            DB_PATH,
            test_claim_id
        )
        
        print("\n--- Gemini Evaluation Result ---")
        print(evaluation_result)
        print("----------------------------------")

    except Exception as e:
        print(f"An error occurred during testing: {e}")


