import re
import ast
import logging
from typing import Tuple, List, Dict

from .sql_tooling import check_document_submission_status, fetch_rule_descriptions_for_ids_from_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _evaluate_logical_expression(expression: str, rule_statuses: Dict[str, bool]) -> bool:
    """
    Safely evaluates the logical expression string by replacing rule IDs with their boolean status
    and then iteratively evaluating the logic from the inside out.
    """
    for rule_id, status in rule_statuses.items():
        expression = expression.replace(rule_id, str(status))

    inner_group_pattern = re.compile(r"([(\[])([\s\w,]+)([)\]])")

    while inner_group_pattern.search(expression):
        for match in inner_group_pattern.finditer(expression):
            operator = match.group(1)
            content = match.group(2)
            
            try:
                bool_list = ast.literal_eval(f"[{content}]")
                if not all(isinstance(x, bool) for x in bool_list):
                    raise ValueError("Non-boolean value detected")
            except Exception as e:
                logging.error(f"Could not parse content: '{content}'. Error: {e}")
                return False

            if operator == '[':
                result = all(bool_list)
            else:
                result = any(bool_list)
            
            expression = expression.replace(match.group(0), str(result), 1)

    return expression == 'True'

def evaluate_submission_logic(expression_string: str, claim_id: str) -> Tuple[bool, List[str]]:
    """
    Parses a logical expression string, checks document submission for each rule, 
    and evaluates the overall logic.
    """
    if not expression_string or not isinstance(expression_string, str):
        logging.warning("Invalid or empty expression string provided for pre-evaluation.")
        return True, []

    rule_ids = sorted(list(set(re.findall(r'\b(CH\d{2})\b', expression_string))))
    if not rule_ids:
        logging.warning(f"No valid rule IDs found in expression: '{expression_string}'. Passing pre-check by default.")
        return True, []

    rule_descriptions = fetch_rule_descriptions_for_ids_from_db(rule_ids)

    rule_statuses = {}
    failed_rules_descriptions = []
    for rule_id in rule_ids:
        description = rule_descriptions.get(rule_id)
        
        if description is None:
            is_submitted = False
            error_message = f"{rule_id}: Rule definition not found in database."
            logging.error(f"For Claim ID {claim_id}, could not find description for {rule_id} in expression '{expression_string}'.")
            failed_rules_descriptions.append(error_message)
        else:
            is_submitted = check_document_submission_status(claim_id, description)
            if not is_submitted:
                failed_rules_descriptions.append(description)
        
        rule_statuses[rule_id] = is_submitted
    
    final_result = _evaluate_logical_expression(expression_string, rule_statuses)
    
    return final_result, failed_rules_descriptions

if __name__ == '__main__':
    print("--- Testing check_rule_evaluator.py ---")

    test_claim_id = "8956"
    print(f"\n--- Running tests for Claim ID: {test_claim_id} ---")

    test_expressions = {
        "1. Simple AND (should pass if CH01 & CH02 submitted)": "[CH01, (CH02, CH03)]",
    }

    for description, expression in test_expressions.items():
        print(f"\n--- Test Case: {description} ---")
        print(f"Expression: '{expression}'")
        
        is_passed, failed_reasons = evaluate_submission_logic(expression, test_claim_id)
        
        print(f"Result: {'PASSED' if is_passed else 'FAILED'}")
        if failed_reasons:
            print("Documents not submitted:")
            for reason in failed_reasons:
                print(f"- {reason}")
        elif not is_passed:
            print("Logic evaluated to False, but no specific document submission failures were found.")
        else:
            print("All checks passed.")
