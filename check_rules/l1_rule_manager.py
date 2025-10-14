import os
import logging
from typing import List, Dict

# Ensure the parent directory is in the system path to allow for absolute imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from check_rules.sql_tooling import (
    fetch_l1_rule_descriptions_with_values,
    fetch_rule_descriptions_for_ids_from_db,
    check_document_submission_status,
    fetch_l1_rule_descriptions
)
from config import RULES_DB_PATH, DB_PATH as CLAIMS_DB_PATH

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_l1_rules_with_values_for_check_id(check_rule_id: str, claim_id: str) -> List[dict]:
    """
    Fetches L1 rule descriptions and values for a given check_rule_id and claim_id.
    It now includes a dependency check on the parent document's submission status.

    Args:
        check_rule_id: The Rule_ID from the Check_Rules table (e.g., 'CH01').
        claim_id: The ClaimID to use in SQL queries.

    Returns:
        A list of dicts, e.g., [{'description': 'Patient Name', 'value': 'John Doe'} or {'description': 'Patient Name', 'value': 'Not submitted'}]
    """
    if not os.path.exists(RULES_DB_PATH):
        logging.error(f"Rules database not found at: {RULES_DB_PATH}. Cannot fetch L1 rules.")
        return []
    if not check_rule_id or not claim_id:
        logging.warning("Check_rule_id or claim_id not provided. Cannot fetch L1 rules.")
        return []

    parent_description_map = fetch_rule_descriptions_for_ids_from_db(RULES_DB_PATH, [check_rule_id])
    parent_description = parent_description_map.get(check_rule_id)

    if not parent_description:
        logging.error(f"Could not find a description for check_rule_id '{check_rule_id}'. Cannot verify submission.")
        return [{'description': f"Configuration error for {check_rule_id}", 'value': 'Cannot verify submission'}]

    is_submitted = check_document_submission_status(claim_id, parent_description, CLAIMS_DB_PATH)

    if not is_submitted:
        l1_rules_descriptions = fetch_l1_rule_descriptions(RULES_DB_PATH, check_rule_id)
        return [{'description': desc, 'value': 'Not submitted'} for desc in l1_rules_descriptions]

    return fetch_l1_rule_descriptions_with_values(RULES_DB_PATH, check_rule_id, CLAIMS_DB_PATH, claim_id)

def get_l1_rules_for_check_id(check_rule_id: str) -> List[str]:
    """
    Fetches L1 rule descriptions for a given check_rule_id using sql_tooling.

    Args:
        check_rule_id: The Rule_ID from the Check_Rules table.

    Returns:
        A list of L1 rule descriptions (str).
        Returns an empty list if no L1 rules are found or an error occurs.
    """
    if not os.path.exists(RULES_DB_PATH):
        logging.error(f"Rules database not found at: {RULES_DB_PATH}. Cannot fetch L1 rules for '{check_rule_id}'.")
        return []
    if not check_rule_id:
        logging.warning("Check_rule_id not provided. Cannot fetch L1 rules.")
        return []

    l1_rules = fetch_l1_rule_descriptions(RULES_DB_PATH, check_rule_id)
    if not l1_rules:
        logging.info(f"No L1 rules found for check_rule_id '{check_rule_id}'.")
    return l1_rules
