import google.generativeai as genai
import os
import tooling 
import json 
import logging # Added to resolve NameError
from dotenv import load_dotenv
from typing import List, Dict, Union

# Load API key from environment variable
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set. Ensure it's defined in your .env file.")

DB_PATH_INFO = os.getenv("DB_PATH", "claim_database.db")

GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", 'gemini-1.5-pro')

TABLE_NAME = tooling.ALLOWED_TABLE

# --- Database Schema (System Prompt) ---
def get_db_columns(db_path, table_name):
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f'PRAGMA table_info("{table_name}");')
    cols = cursor.fetchall()
    conn.close()
    return [f'- "{col[1]}" {col[2]}' for col in cols]

columns_list = get_db_columns(DB_PATH_INFO, TABLE_NAME)
columns_str = '\n'.join(columns_list)

DATABASE_SCHEMA = f"""
You are an AI assistant designed to answer questions about medical claims data stored in a SQLite database.
You have access to a specific tool, 'execute_sql_query', which allows you to run read-only (SELECT) queries against the database.

Database Details:
- The database contains only one table relevant to your queries: '{TABLE_NAME}'.
- This table stores consolidated data extracted from various claim documents.

Table Schema: '{TABLE_NAME}'

Columns:
{columns_str}

Querying Instructions & Rules:
1. Tool Use: You MUST use the 'execute_sql_query' tool to answer questions requiring data from the database. Do not make up answers.
2. SQL Generation:
    - Generate only valid SQLite SELECT queries.
    - CRITICAL: Column names containing periods or special characters MUST be enclosed in double quotes (e.g., SELECT "Claim_form_page_1.Patient_Name" FROM {TABLE_NAME}).
    - Always specify the table name: FROM {TABLE_NAME}.
    - Use the ClaimID column in a WHERE clause to filter for specific records when the user provides a Claim ID (e.g., WHERE ClaimID = 123).
    - When asked if a value "exists" or was "submitted" (like Rohini ID, Surgery name), check if the column is not NULL AND not an empty string (e.g., WHERE "Claim_form_page_1.Rohini_ID" IS NOT NULL AND "Claim_form_page_1.Rohini_ID" <> '').
3. Interpreting Results:
    - The tool will return results as a JSON string representing a list of rows (dictionaries).
    - If the query returns an empty list ([]), it means no records matched the criteria. Inform the user clearly.
    - If a specific field within a returned row is null or empty, state that the information is missing or not provided for that claim.
    - If the tool returns a JSON object indicating an error (e.g., containing an "error" key like '{{{{\"error\": \"message\"}}}}'), inform the user that there was a problem retrieving the data and mention the error if appropriate (e.g., "Database error occurred"). Do not attempt to re-run the same failed query unless the user modifies the request.
4. Response Format: Answer the user's question directly based only on the information returned by the tool. Be concise and clear.
"""

RULE_CHECKING_PROMPT_TEMPLATE = f"""
You are an AI assistant designed to evaluate specific rules against medical claims data stored in a SQLite database table named '{TABLE_NAME}'.
Your goal is to determine if the given rule is met and provide a concise answer, along with supporting details if applicable (e.g., count of matching records, example ClaimIDs).

You have access to a tool, 'execute_sql_query', which allows you to run read-only (SELECT) queries against the '{TABLE_NAME}' table.

Table Schema: '{TABLE_NAME}'
Columns:
{columns_str}

{{claim_id_instruction}}

Querying Instructions & Rules:
1. Tool Use: You MUST use the 'execute_sql_query' tool to answer questions requiring data from the database. Do not make up answers.
2. SQL Generation:
    - Generate only valid SQLite SELECT queries.
    - CRITICAL: Column names containing periods or special characters MUST be enclosed in double quotes (e.g., SELECT "Claim_form_page_1.Patient_Name" FROM {TABLE_NAME}).
    - Always specify the table name: FROM {TABLE_NAME}.
    - When asked if a value "exists" or was "submitted" (like Rohini ID, Surgery name), check if the column is not NULL AND not an empty string (e.g., WHERE "Claim_form_page_1.Rohini_ID" IS NOT NULL AND "Claim_form_page_1.Rohini_ID" <> '').
    {{general_querying_rules_extension}}
3. Interpreting Results:
    - The tool will return results as a JSON string representing a list of rows (dictionaries) or an error object.
    - If the query returns an empty list ([]), it means no records matched the criteria. Inform the user clearly.
    - If a specific field within a returned row is null or empty, state that the information is missing or not provided for that claim.
    - If the tool returns a JSON object indicating an error (e.g., containing an "error" key like '{{{{\"error\": \"message\"}}}}'), inform the user that there was a problem retrieving the data and mention the error if appropriate (e.g., "Database error occurred"). Do not attempt to re-run the same failed query unless the user modifies the request.
4. Response Format: Answer the user's question directly based only on the information returned by the tool. Be concise and clear.
    - Example: "Yes, the rule is met. 5 claims match this condition. (e.g., ClaimIDs: 101, 102, 103, 104, 105)"
    - Example: "No, the rule is not met. No claims match this condition."
    - Example: "Unable to evaluate rule due to a database error: [error message from tool]"
    - Be concise. Avoid conversational fluff unless necessary to clarify the result.
"""

def get_rule_checking_prompt(claim_id: str = None) -> str:
    """Generates the system prompt for rule checking, optionally scoping to a ClaimID."""
    claim_id_instruction_text = ""
    general_querying_rules_extension_text = "- Use the ClaimID column in a WHERE clause to filter for specific records when the user provides a Claim ID (e.g., WHERE ClaimID = 123)."
    if claim_id:
        claim_id_instruction_text = f"""CRITICAL INSTRUCTION: You MUST evaluate the current rule ONLY for ClaimID \"{claim_id}\". 
All SQL queries you generate MUST include 'WHERE ClaimID = \"{claim_id}\"' to target this specific claim. 
Do not query other claims for this rule."""
        general_querying_rules_extension_text = ""
    
    return RULE_CHECKING_PROMPT_TEMPLATE.format(
        claim_id_instruction=claim_id_instruction_text,
        general_querying_rules_extension=general_querying_rules_extension_text
    ).strip()

sql_tool = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name='execute_sql_query',
            description=f"Executes a read-only (SELECT) SQL query against the {TABLE_NAME} table in the SQLite database to retrieve claim information. Returns results as a JSON string.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    'sql_query': genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description=f"The SQLite SELECT query targeting the {TABLE_NAME} table. Column names with periods or special characters MUST be enclosed in double quotes."
                        )
                },
                required=['sql_query']
            )
        )
    ]
)

def check_single_rule(rule_text: str, claim_id: str = None) -> str:
    """Processes a single rule using Gemini and returns the textual response.
    Optionally scopes the rule evaluation to a specific claim_id.
    """
    logging.info(f"Checking single rule: '{rule_text}' for ClaimID: {claim_id if claim_id else 'Any'}")
    try:
        genai.configure(api_key=API_KEY)
        
        final_system_prompt = get_rule_checking_prompt(claim_id)
        logging.debug(f"Using system prompt for check_single_rule (ClaimID: {claim_id}):\n{final_system_prompt}")

        model = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            generation_config=genai.types.GenerationConfig(temperature=0.1),
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
            system_instruction=final_system_prompt, 
            tools=[sql_tool]
        )

        chat = model.start_chat(
            enable_automatic_function_calling=False
        )

        logging.info(f"Sending rule to Gemini: {rule_text}")
        response = chat.send_message(rule_text)

        if response.parts and response.parts[0].function_call:
            function_call = response.parts[0].function_call
            tool_name = function_call.name
            logging.info(f"Gemini requested function call: {tool_name}")

            if tool_name == 'execute_sql_query':
                args = dict(function_call.args)
                sql_query_to_execute = args.get('sql_query')
                if sql_query_to_execute:
                    logging.info(f"Extracted SQL query: {sql_query_to_execute}")
                    tool_result_json_str = tooling.execute_sql_query(sql_query_to_execute)
                    logging.info(f"Tool execution result (JSON String): {tool_result_json_str}")
                    
                    try:
                        tool_result_data = json.loads(tool_result_json_str)
                    except json.JSONDecodeError as e:
                        logging.error(f"JSONDecodeError parsing tool result: {e}. Raw string: {tool_result_json_str}")
                        tool_result_data = {"error": "Failed to parse SQL tool result", "details": str(e), "raw_output": tool_result_json_str}

                    gemini_response_payload: dict
                    if isinstance(tool_result_data, list):
                        gemini_response_payload = {"records": tool_result_data}
                    elif isinstance(tool_result_data, dict):
                        gemini_response_payload = tool_result_data 
                    else:
                        logging.warning(f"Tool result data is neither list nor dict: {type(tool_result_data)}. Wrapping it in 'data' key.")
                        gemini_response_payload = {"data": tool_result_data}

                    logging.debug(f"[rules_agent] check_single_rule: Preparing FunctionResponse. gemini_response_payload type: {type(gemini_response_payload)}, content: {json.dumps(gemini_response_payload, indent=2)}")
                    response = chat.send_message(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_name,
                                response=gemini_response_payload
                            )
                        )
                    )
                    return response.text 

                else:
                    logging.error("SQL query missing in function call arguments.")
                    return "Error: Gemini requested a database query but the query was missing."
            else:
                logging.error(f"Received request for unknown tool: {tool_name}")
                return f"Error: Gemini requested an unknown tool: {tool_name}"
        else:
            return response.text

    except genai.types.StopCandidateException as stop_err:
        logging.warning(f"Rule check response stopped. Reason: {stop_err.finish_reason}")
        safety_info = f" (Safety Ratings: {stop_err.safety_ratings})" if hasattr(stop_err, 'safety_ratings') and stop_err.safety_ratings else ""
        return f"Rule evaluation stopped: {stop_err.finish_reason}{safety_info}"
    except Exception as e:
        logging.exception("Error in check_single_rule:")
        return f"An error occurred while checking the rule: {str(e)}"


def check_rules_from_file(file_content_string: str, claim_id: str = None) -> list[dict[str, str]]:
    """Processes multiple rules from a file content string, calling check_single_rule for each.
    Optionally scopes all rule evaluations to a specific claim_id.
    Returns a list of dictionaries containing the rule and its result."""
    rules = [rule.strip() for rule in file_content_string.splitlines() if rule.strip()]
    if not rules:
        return [{'Rule': 'N/A', 'Result': 'No rules found in the file or file is empty.'}]

    processed_rules = []
    for i, rule_text in enumerate(rules):
        log_prefix = f"Rule {i+1}/{len(rules)} ('{rule_text[:50]}...')"
        if claim_id:
            log_prefix += f" for ClaimID {claim_id}"
        logging.info(f"Processing {log_prefix}")
        try:
            result = check_single_rule(rule_text, claim_id)
            processed_rules.append({'Rule': rule_text, 'Result': result})
        except Exception as e:
            logging.error(f"Error processing rule '{rule_text}' from file: {e}", exc_info=True)
            processed_rules.append({'Rule': rule_text, 'Result': f"Error evaluating rule: {e}"})
    
    return processed_rules


def run_chat_agent():
    """Initializes and runs the chat agent loop."""

    print("Initializing Gemini Agent...")
    try:
        genai.configure(api_key=API_KEY)

        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL_NAME,
            system_instruction=DATABASE_SCHEMA,
            tools=[sql_tool]
        )

        chat = model.start_chat() 

        print("-" * 30)
        print(f"Chat Agent Ready!")
        print(f" Model: {GEMINI_MODEL_NAME}")
        print(f" Database Path: {DB_PATH_INFO}")
        print(f" Target Table: {TABLE_NAME}")
        print("-" * 30)
        print("Ask questions about the claims data (e.g., 'What is the Rohini ID for ClaimID 123?').")
        print("Type 'quit' or 'exit' to end.")
        print("-" * 30)

    except Exception as init_err:
        print(f"\nError initializing Gemini Agent: {init_err}")
        print("Please check your API key, network connection, and model name.")
        return

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ['exit', 'quit']:
            print("Exiting chat agent.")
            break

        logging.info(f"User input: {user_input}")
        try:
            response = chat.send_message(user_input)
            
            if response.parts and response.parts[0].function_call:
                function_call = response.parts[0].function_call
                tool_name = function_call.name
                logging.info(f"Gemini requested function call: {tool_name}")

                if tool_name == 'execute_sql_query':
                    args = dict(function_call.args)
                    sql_query_to_execute = args.get('sql_query')
                    if sql_query_to_execute:
                        logging.info(f"Extracted SQL query: {sql_query_to_execute}")
                        tool_result_json_str = tooling.execute_sql_query(sql_query_to_execute)
                        logging.info(f"Tool execution result (JSON String): {tool_result_json_str}")
                        
                        try:
                            tool_result_data = json.loads(tool_result_json_str)
                            if isinstance(tool_result_data, list):
                                gemini_response_payload = {"result": tool_result_data}
                                logging.debug(f"Original list result wrapped into dict: {gemini_response_payload}")
                            elif isinstance(tool_result_data, dict):
                                gemini_response_payload = tool_result_data
                            else:
                                gemini_response_payload = {"error": "Unexpected tool result format", "details": tool_result_json_str}
                                logging.error(f"Unexpected tool result format: {type(tool_result_data)}, payload: {tool_result_json_str}")

                        except json.JSONDecodeError as e:
                            logging.error(f"JSONDecodeError from tool result: {e}. Raw string: {tool_result_json_str}")
                            gemini_response_payload = {"error": "Tool returned invalid JSON", "details": tool_result_json_str}

                        logging.debug(f"Sending function response to Gemini, type: {type(gemini_response_payload)}, content: {str(gemini_response_payload)[:500]}...")
                        response = chat.send_message(
                            genai.protos.Part(function_response=genai.protos.FunctionResponse(
                                name='execute_sql_query',
                                response=gemini_response_payload
                            ))
                        )
                        if response.parts:
                            print(f"Gemini: {response.text}")
                        else:
                            print("Gemini: (No textual response after function call)")
                    else:
                        logging.warning("execute_sql_query called by Gemini, but 'sql_query' argument was missing or empty.")
                        print("Gemini: (Internal note: Tried to call SQL tool without a query)")
                else:
                    logging.warning(f"Gemini requested unknown tool: {tool_name}")
                    print(f"Gemini: (Internal note: Tried to use an unknown tool: {tool_name})")
            
            elif response.parts and response.text:
                print(f"Gemini: {response.text}")
            else:
                logging.warning("Gemini response was empty or had no processable parts.")
                print("Gemini: (No response or unprocessable content)")
        
        except Exception as e:
            logging.error(f"Error during chat loop: {e}", exc_info=True)
            print(f"An error occurred: {e}")

if __name__ == '__main__':
    run_chat_agent()