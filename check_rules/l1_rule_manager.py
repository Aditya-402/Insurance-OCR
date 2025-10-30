import logging
from typing import List, Dict

from .sql_tooling import (
    fetch_l1_rule_descriptions_with_values,
    fetch_rule_descriptions_for_ids_from_db,
    check_document_submission_status,
    fetch_l1_rule_descriptions
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_l1_rules_with_values_for_check_id(check_rule_id: str, claim_id: str) -> List[dict]:
    """
    Fetches L1 rule descriptions and values for a given check_rule_id and claim_id.
    It now includes a dependency check on the parent document's submission status.
    """
    if not check_rule_id or not claim_id:
        logging.warning("Check_rule_id or claim_id not provided. Cannot fetch L1 rules.")
        return []

    parent_description_map = fetch_rule_descriptions_for_ids_from_db([check_rule_id])
    parent_description = parent_description_map.get(check_rule_id)

    if not parent_description:
        logging.error(f"Could not find a description for check_rule_id '{check_rule_id}'. Cannot verify submission.")
        return [{'description': f"Configuration error for {check_rule_id}", 'value': 'Cannot verify submission'}]

    is_submitted = check_document_submission_status(claim_id, parent_description)

    if not is_submitted:
        l1_rules_descriptions = fetch_l1_rule_descriptions(check_rule_id)
        return [{'description': desc, 'value': 'Not submitted'} for desc in l1_rules_descriptions]

    return fetch_l1_rule_descriptions_with_values(check_rule_id, claim_id)

def get_l1_rules_for_check_id(check_rule_id: str) -> List[str]:
    """
    Fetches L1 rule descriptions for a given check_rule_id using sql_tooling.
    """
    if not check_rule_id:
        logging.warning("Check_rule_id not provided. Cannot fetch L1 rules.")
        return []

    l1_rules = fetch_l1_rule_descriptions(check_rule_id)
    if not l1_rules:
        logging.info(f"No L1 rules found for check_rule_id '{check_rule_id}'.")
    return l1_rules
