import os
import logging
import re
from typing import List, Optional, Dict
from .sql_tooling import (
    fetch_all_procedure_names_from_db, 
    fetch_rules_for_procedure_from_db,
    fetch_rule_descriptions_for_ids_from_db,
    fetch_l1_rule_descriptions_with_values,
    fetch_procedure_rules_expression_from_db,
    check_document_submission_status, # Added to fix NameError
    fetch_l1_rule_descriptions # Added to support the new logic
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the centralized path for the rules database
from .config import RULES_DB_PATH

def get_procedure_names() -> List[str]:
    """
    Fetches all procedure names from the Procedure_rules table using rule_queries.

    Returns:
        A list of procedure names (str).
        Returns an empty list if the database cannot be accessed or no names are found.
    """
    if not os.path.exists(RULES_DB_PATH):
        logging.error(f"Rules database not found at: {RULES_DB_PATH}. Cannot fetch procedure names.")
        return []
    
    procedure_names = fetch_all_procedure_names_from_db(RULES_DB_PATH)
    if not procedure_names:
        logging.warning(f"No procedure names returned from {RULES_DB_PATH}.")
    return procedure_names

def get_rules_for_procedure(procedure_name: str) -> List[str]:
    """
    Fetches and formats the rules for a given procedure name.
    First, it gets the list of rule IDs for the procedure.
    Then, it fetches the description for each rule ID and formats it.

    Args:
        procedure_name: The name of the procedure.

    Returns:
        A list of formatted strings, e.g., ["CH01: Description for rule 1."].
        Returns a list with an error message if not found.
    """
    if not procedure_name:
        logging.warning("Procedure name not provided. Cannot fetch rules.")
        return []

    # Step 1: Get the clean list of rule IDs using the new parsing function.
    parsed_rule_ids = get_parsed_rules_for_procedure(procedure_name)
    if not parsed_rule_ids:
        logging.warning(f"No rule IDs returned for procedure '{procedure_name}'.")
        return [f"No Rule IDs found for procedure: {procedure_name}"]

    # Step 2: Fetch the descriptions for these clean IDs.
    descriptions_map = fetch_rule_descriptions_for_ids_from_db(RULES_DB_PATH, parsed_rule_ids)
    
    # Step 3: Format the final list for the UI.
    formatted_rules = []
    for rid in parsed_rule_ids:
        # If a description is missing, we note it, but don't crash.
        desc = descriptions_map.get(rid, "Description not found.")
        formatted_rules.append(f"{rid}: {desc}")
    
    if not formatted_rules:
        logging.warning(f"No descriptions could be formatted for '{procedure_name}'. Rule IDs: {parsed_rule_ids}")
        return [f"Could not retrieve descriptions for Rule IDs: {', '.join(parsed_rule_ids)}"]
        
    return formatted_rules



def get_procedure_rules_expression(procedure_name: str) -> Optional[str]:
    """
    Fetches the 'procedure_rules' expression string for a given procedure name.

    Args:
        procedure_name: The name of the procedure.

    Returns:
        The expression string (e.g., "[CH01, (CH02, CH13)]") or None if not found.
    """
    if not os.path.exists(RULES_DB_PATH):
        logging.error(f"Rules database not found at: {RULES_DB_PATH}. Cannot fetch expression for '{procedure_name}'.")
        return None
    if not procedure_name:
        logging.warning("Procedure name not provided. Cannot fetch expression.")
        return None

    return fetch_procedure_rules_expression_from_db(RULES_DB_PATH, procedure_name)


def get_parsed_rules_for_procedure(procedure_name: str) -> List[str]:
    """
    Fetches the 'Check_Rules' string for a procedure and parses it into a clean list of rule IDs.
    This is the definitive method for getting rules and handles parsing issues.

    Args:
        procedure_name: The name of the procedure.

    Returns:
        A list of clean rule IDs (e.g., ['CH01', 'CH02']) or an empty list if none are found.
    """
    if not os.path.exists(RULES_DB_PATH):
        logging.error(f"Rules database not found at: {RULES_DB_PATH}. Cannot fetch rules for '{procedure_name}'.")
        return []

    # Fetch the raw string which might contain brackets, etc.
    raw_rules_string = fetch_rules_for_procedure_from_db(RULES_DB_PATH, procedure_name)

    if not raw_rules_string:
        return []

    # Use regex to find all occurrences of 'CH' followed by digits, ensuring clean extraction.
    parsed_rule_ids = re.findall(r'\b(CH\d{2,})\b', raw_rules_string)
    
    logging.info(f"Parsed rules for '{procedure_name}': {parsed_rule_ids}")
    return parsed_rule_ids




# Example of how to use the functions (for testing purposes)
if __name__ == '__main__':
    print("--- Testing rule_db_manager.py ---")
    print(f"Using RULES_DB_PATH: {RULES_DB_PATH}")

    if not os.path.exists(RULES_DB_PATH):
        print(f"Error: Database file not found at {RULES_DB_PATH}. Please ensure it exists and is correctly populated.")
    else:
        print("\nAttempting to fetch procedure names...")
        names = get_procedure_names()
        if names:
            print("Found procedure names:")
            for name in names:
                print(f"- {name}")
            
            selected_proc_to_test = names[0]
            print(f"\nAttempting to fetch rules and descriptions for procedure: '{selected_proc_to_test}'...")
            formatted_rule_list = get_rules_for_procedure(selected_proc_to_test)
            if formatted_rule_list:
                print(f"Formatted Rules for '{selected_proc_to_test}':")
                for item in formatted_rule_list:
                    print(f"- {item}")
            else:
                print(f"No rules/descriptions found or an error occurred for '{selected_proc_to_test}'.")
        else:
            print("No procedure names found or an error occurred during fetching.")

        # Test get_l1_rules_for_check_id
        if names: # Only test if we have procedures, and thus potential check_rule_ids
            # Assuming the first rule of the first procedure is a valid check_rule_id for testing L1 rules
            # This is a simplification; in a real test, you'd use a known check_rule_id
            if formatted_rule_list and ":" in formatted_rule_list[0]:
                first_check_rule_id_to_test = formatted_rule_list[0].split(":")[0].strip()
                print(f"\nAttempting to fetch L1 rules for check_rule_id: '{first_check_rule_id_to_test}'...")
                l1_rule_list = get_l1_rules_for_check_id(first_check_rule_id_to_test)
                if l1_rule_list:
                    print(f"L1 Rules for '{first_check_rule_id_to_test}':")
                    for item in l1_rule_list:
                        print(f"- {item}")
                else:
                    print(f"No L1 rules found for '{first_check_rule_id_to_test}'.")
            else:
                print("Skipping L1 rule test as no valid check_rule_id could be extracted from fetched rules.")
