import re
import ast
import logging
from typing import Tuple, List, Dict

from config import RULES_DB_PATH, DB_PATH as CLAIMS_DB_PATH
from .sql_tooling import check_document_submission_status, fetch_rule_descriptions_for_ids_from_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _evaluate_logical_expression(expression: str, rule_statuses: Dict[str, bool]) -> bool:
    """
    Safely evaluates the logical expression string by replacing rule IDs with their boolean status
    and then iteratively evaluating the logic from the inside out.
    """
    # 1. Replace all rule IDs with their boolean status.
    for rule_id, status in rule_statuses.items():
        expression = expression.replace(rule_id, str(status))

    # 2. Iteratively evaluate inner expressions until only True/False remains.
    # Regex to find the innermost groups, e.g., (True, False) or [True, True]
    inner_group_pattern = re.compile(r"([(\[])([\s\w,]+)([)\]])")

    while inner_group_pattern.search(expression):
        for match in inner_group_pattern.finditer(expression):
            operator = match.group(1)  # '[' or '('
            content = match.group(2)   # 'True, False'
            
            # Convert content string to a list of booleans safely
            try:
                bool_list = ast.literal_eval(f"[{content}]")
                # Validate that all elements are booleans
                if not all(isinstance(x, bool) for x in bool_list):
                    raise ValueError("Non-boolean value detected")
            except Exception as e:
                logging.error(f"Could not parse content: '{content}'. Error: {e}")
                return False # Cannot parse, fail safely

            # Apply the correct Python function
            if operator == '[': # AND logic
                result = all(bool_list)
            else: # OR logic
                result = any(bool_list)
            
            # Replace the evaluated part of the string with its boolean result
            expression = expression.replace(match.group(0), str(result), 1)

    # 3. Final result should be a single 'True' or 'False' string
    return expression == 'True'

def evaluate_submission_logic(expression_string: str, claim_id: str) -> Tuple[bool, List[str]]:
    """
    Parses a logical expression string, checks document submission for each rule, 
    and evaluates the overall logic.

    Args:
        expression_string: The logical string, e.g., "[CH01, (CH02, CH13)]".
        claim_id: The claim ID to check submission status for.

    Returns:
        A tuple containing:
        - bool: The final evaluation result (True if logic passes, False otherwise).
        - list: A list of failed rule descriptions for user feedback.
    """
    if not expression_string or not isinstance(expression_string, str):
        logging.warning("Invalid or empty expression string provided for pre-evaluation.")
        # If no expression is defined, default to passing the pre-check
        return True, []

    # 1. Find all unique rule IDs (e.g., 'CH01') in the expression
    # 1. Find all unique rule IDs (e.g., 'CH01') in the expression using word boundaries
    rule_ids = sorted(list(set(re.findall(r'\b(CH\d{2})\b', expression_string))))
    if not rule_ids:
        logging.warning(f"No valid rule IDs found in expression: '{expression_string}'. Passing pre-check by default.")
        return True, []

    # 2. Get descriptions for all rule IDs in one DB call
    rule_descriptions = fetch_rule_descriptions_for_ids_from_db(RULES_DB_PATH, rule_ids)

    # 3. Check submission status for each rule
    rule_statuses = {}
    failed_rules_descriptions = []
    for rule_id in rule_ids:
        description = rule_descriptions.get(rule_id)
        
        # If description is not found in the DB, the rule automatically fails.
        if description is None:
            is_submitted = False
            error_message = f"{rule_id}: Rule definition not found in database."
            logging.error(f"For Claim ID {claim_id}, could not find description for {rule_id} in expression '{expression_string}'.")
            failed_rules_descriptions.append(error_message)
        else:
            # The keyword for checking is the description itself
            is_submitted = check_document_submission_status(claim_id, description, CLAIMS_DB_PATH)
            if not is_submitted:
                failed_rules_descriptions.append(description)
        
        rule_statuses[rule_id] = is_submitted
    
    # 4. Evaluate the expression
    final_result = _evaluate_logical_expression(expression_string, rule_statuses)
    
    return final_result, failed_rules_descriptions

if __name__ == '__main__':

    #evaluate_submission_logic("[CH01, CH02]", "8956")
    print("--- Testing check_rule_evaluator.py ---")

    # This test suite relies on the 'except ImportError' block at the top for path configuration.
    print(f"Using RULES_DB_PATH: {RULES_DB_PATH}")
    print(f"Using CLAIMS_DB_PATH: {CLAIMS_DB_PATH}")

    # Use a claim_id that exists in your test database.
    test_claim_id = "8956"
    print(f"\n--- Running tests for Claim ID: {test_claim_id} ---")

    # Define a dictionary of test cases to run.
    test_expressions = {
        "1. Simple AND (should pass if CH01 & CH02 submitted)": "[CH01, (CH02, CH03)]",
        #"2. Simple OR (should pass if CH01 or CH04 submitted)": "(CH01, CH04)",
        #"3. Complex Nested (should pass if CH01 and (CH02 or CH13) submitted)": "[CH01, (CH02, CH13)]",
        #"4. Simple AND (should fail if CH04 not submitted)": "[CH01, CH04]",
        #"5. Complex with Fail (should fail if CH04 not submitted)": "[CH01, (CH04, CH13)]",
        #"6. Non-existent Rule (should fail)": "[CH01, CH99]",
        #"7. Empty Expression (should pass by default)": "",
        #"8. Invalid Expression (should pass by default)": "CH01 AND CH02",
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
