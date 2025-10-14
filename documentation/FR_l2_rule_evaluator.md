# Functional Requirements for l2_rule_evaluator.py

## 1. Overview

This document outlines the functional requirements for the `l2_rule_evaluator.py` script. The script's primary purpose is to evaluate Level 2 (L2) business rules using Google's Gemini Pro API. It can handle both simple data checks and complex, multi-source validations by dynamically constructing prompts and interpreting structured responses from the AI model.

## 2. Functional Requirements

### REQ-L2G-001: Gemini-Based Rule Evaluation
The system shall provide a single function, `evaluate_l2_rule_with_gemini`, to serve as the entry point for L2 rule evaluation.

### REQ-L2G-002: Input Parameters
The function shall accept the following parameters:
- `l2_description`: A natural language string describing the rule to be evaluated.
- `l1_value`: A string containing either a simple value or a comma-separated list of L1 rule references.
- `rules_db_path`: The file path to the rules database.
- `claims_db_path`: The file path to the claims database.
- `claim_id`: The identifier for the specific claim being processed.

### REQ-L2G-003: Dual Evaluation Modes
The system shall operate in one of two modes based on the content of the `l1_value` parameter.

#### REQ-L2G-003-1: Complex Evaluation Mode
If `l1_value` contains L1 rule IDs (e.g., `L1_01_06`), the system shall:
- Parse the string to identify all referenced L1 rules and their corresponding document sources.
- For each L1 rule, fetch the underlying data by calling the `_fetch_data_for_l1_rule` function from `sql_tooling`.
- Load a prompt template from an external file (`prompts/gemini_2-5f_l2_evaluation_prompt.txt`).
- Construct a detailed prompt by populating the template with the L2 description and the fetched L1 data.
- Request a structured JSON response from the Gemini model.

#### REQ-L2G-003-2: Simple Evaluation Mode
If `l1_value` does not contain L1 rule IDs, the system shall:
- Construct a basic prompt asking for a simple 'Pass', 'Fail', or 'Cannot Determine' judgment.
- Request a plain text response from the Gemini model.

### REQ-L2G-004: Structured JSON Response Handling
REQ-L2G-004-1: For complex evaluations, the system shall expect a JSON object from the Gemini API.

REQ-L2G-004-2: The system shall parse and validate the JSON, ensuring it contains the keys: `primary_source`, `comparisons`, `overall_decision`, and `overall_reasoning`.

REQ-L2G-004-3: If the JSON is incomplete or malformed, the system shall return a 'Cannot Determine' status with a descriptive reason.

### REQ-L2G-005: Simple Text Response Handling
For simple evaluations, the system shall parse the plain text response, clean it, and return a dictionary with the decision and a standard reason.

### REQ-L2G-006: Return Value
The function shall return a dictionary containing the evaluation result or a string in case of a critical error.

### REQ-L2G-007: Error Handling
The system shall gracefully handle potential errors, including:
- `FileNotFoundError` if the prompt template is missing.
- `json.JSONDecodeError` if the API response is not valid JSON.
- General exceptions during API calls or data fetching, logging them appropriately.

### REQ-L2G-008: Script Execution
The script shall be executable as a standalone module. When run directly, it should execute a test case with sample data to demonstrate and verify its functionality.

## 3. Implementation Details

The following table maps the functional requirements to the specific components within the `l2_rule_evaluator.py` script.

| Component Name                  | Description                                                                                             | Related Requirements                               | 
| ------------------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `evaluate_l2_rule_with_gemini`  | The main function that orchestrates the entire Gemini-based rule evaluation.                            | REQ-L2G-001, 002, 003, 004, 005, 006, 007         |
| `if __name__ == '__main__'`     | Contains a test block for demonstrating the script's functionality when run directly.                   | REQ-L2G-008                                        |

## 4. Dependencies

The script relies on the following external and internal modules.

| Library/Module                  | Notes                                                              | 
| ------------------------------- | ------------------------------------------------------------------ | 
| `os`, `re`, `logging`, `json`   | Standard Python libraries for system interaction and data handling.| 
| `typing`                        | Standard library for type hints.                                   | 
| `config.get_gemini_model`       | Internal module for initializing the configured Gemini model.      | 
| `sql_tooling._fetch_data_for_l1_rule` | Internal module for fetching L1 data from the database.            | 
