import os
import logging
import re
from typing import List, Optional

from .sql_tooling import (
    fetch_all_procedure_names_from_db, 
    fetch_rules_for_procedure_from_db,
    fetch_rule_descriptions_for_ids_from_db,
    fetch_procedure_rules_expression_from_db
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_procedure_names() -> List[str]:
    """
    Fetches all procedure names from the Procedure_rules table.
    """
    return fetch_all_procedure_names_from_db()

def get_rules_for_procedure(procedure_name: str) -> List[str]:
    """
    Fetches and formats the rules for a given procedure name.
    """
    if not procedure_name:
        logging.warning("Procedure name not provided. Cannot fetch rules.")
        return []

    parsed_rule_ids = get_parsed_rules_for_procedure(procedure_name)
    if not parsed_rule_ids:
        logging.warning(f"No rule IDs returned for procedure '{procedure_name}'.")
        return [f"No Rule IDs found for procedure: {procedure_name}"]

    descriptions_map = fetch_rule_descriptions_for_ids_from_db(parsed_rule_ids)
    
    formatted_rules = []
    for rid in parsed_rule_ids:
        desc = descriptions_map.get(rid, "Description not found.")
        formatted_rules.append(f"{rid}: {desc}")
    
    if not formatted_rules:
        logging.warning(f"No descriptions could be formatted for '{procedure_name}'. Rule IDs: {parsed_rule_ids}")
        return [f"Could not retrieve descriptions for Rule IDs: {', '.join(parsed_rule_ids)}"]
        
    return formatted_rules

def get_procedure_rules_expression(procedure_name: str) -> Optional[str]:
    """
    Fetches the 'procedure_rules' expression string for a given procedure name.
    """
    return fetch_procedure_rules_expression_from_db(procedure_name)

def get_parsed_rules_for_procedure(procedure_name: str) -> List[str]:
    """
    Fetches the 'Check_Rules' string for a procedure and parses it into a clean list of rule IDs.
    """
    raw_rules_string = fetch_rules_for_procedure_from_db(procedure_name)

    if not raw_rules_string:
        return []

    parsed_rule_ids = re.findall(r'\b(CH\d{2,})\b', raw_rules_string)
    
    logging.info(f"Parsed rules for '{procedure_name}': {parsed_rule_ids}")
    return parsed_rule_ids

if __name__ == '__main__':
    print("--- Testing rule_db_manager.py ---")
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
            print(f"No rules/descriptions found for '{selected_proc_to_test}'.")
    else:
        print("No procedure names found or an error occurred during fetching.")
