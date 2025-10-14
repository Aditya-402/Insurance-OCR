import google.generativeai as genai
import os
import tooling 
import json 
import logging
from dotenv import load_dotenv
from typing import List, Optional

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load API key from environment variable
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set. Ensure it's defined in your .env file.")

DB_PATH_INFO = os.getenv("DB_PATH", "claim_database.db")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", 'gemini-1.5-pro')
TABLE_NAME = tooling.ALLOWED_TABLE

# Fetch column names for the prompt
try:
    columns_list = tooling.get_db_columns(DB_PATH_INFO, TABLE_NAME)
    columns_str = '\n'.join([f'- "{col}"' for col in columns_list])
except Exception as e:
    logging.error(f"Failed to get DB columns for {TABLE_NAME}: {e}")
    columns_str = "[Could not load columns]"

# System prompt template for SQL generation
SQL_GENERATION_PROMPT_TEMPLATE = """
You are an AI assistant that translates natural language questions into SQLite SELECT queries.
Your goal is to generate a syntactically correct SQLite SELECT query that will retrieve the answer to the given question from the specified table, considering the provided columns and a specific ClaimID.

Instructions:
1.  You will be given a natural language question, a target table name, a list of available column names for that table, and a specific ClaimID.
2.  The generated SQL query MUST be a SELECT statement.
3.  The query MUST target the specified `table_name`.
4.  The query MUST use ONLY columns from the provided `column_list`.
5.  The query MUST include a WHERE clause to filter by the specific `ClaimID`. Use a placeholder for the ClaimID value (e.g., `WHERE ClaimID = ?`).
6.  If the question asks for a specific piece of information (e.g., "What is the Customer ID?"), the SELECT clause should retrieve that specific column.
7.  If the question is a yes/no type (e.g., "Is the policy active?"), the query should select the relevant column(s) that would help determine the answer.
8.  CRITICAL: Your response MUST be ONLY the SQL query string itself. Do not include any explanations, markdown, or any other text before or after the SQL query.

Example Input:
Question: "What is the patient's date of birth?"
Table Name: "PatientData"
Columns: ["ClaimID", "PatientName", "DateOfBirth", "PolicyNumber"]
ClaimID: "XYZ123"

Example Output:
SELECT DateOfBirth FROM PatientData WHERE ClaimID = ?
"""

# System prompt template for the Gemini model
RULE_CHECKING_PROMPT_TEMPLATE = f"""
You are an AI assistant designed to evaluate specific rules against medical claims data stored in a SQLite database table named '{TABLE_NAME}'.
Your goal is to determine if the given rule is met and provide a concise answer, along with supporting details if applicable (e.g., count of matching records, example ClaimIDs).

You have access to a tool, 'execute_sql_query', which allows you to run read-only (SELECT) queries against the '{TABLE_NAME}' table.

Table Schema: '{TABLE_NAME}'
Columns:
{columns_str}

{{claim_id_instruction}}

Querying Instructions & Rules:
1. Tool Use: You MUST use the 'execute_sql_query' tool to answer questions. Do not make up answers.
2. SQL Generation:
    - Generate only valid SQLite SELECT queries.
    - CRITICAL: Column names containing periods or special characters MUST be enclosed in double quotes (e.g., SELECT "Claim_form_page_1.Patient_Name" FROM {TABLE_NAME}).
    - Always specify the table name: FROM {TABLE_NAME}.
    - When asked if a value "exists" or was "submitted" (like Rohini ID, Surgery name), check if the column is not NULL AND not an empty string (e.g., WHERE "Claim_form_page_1.Rohini_ID" IS NOT NULL AND "Claim_form_page_1.Rohini_ID" <> '').
    {{general_querying_rules_extension}}
3. Interpreting Results:
    - The tool returns results as a JSON string representing a list of rows (dictionaries) or an error object.
    - If the query returns an empty list ([]), no records matched. Inform the user clearly.
    - If a field in a returned row is null or empty, state that the information is missing.
    - If the tool returns a JSON object with an "error" key, inform the user about the database error.
4. Response Format: Answer the user's question directly based only on the tool's information. Be concise.
    - Example: "Yes, the rule is met. 5 claims match this condition."
    - Example: "No, the rule is not met. No claims match this condition."
    - Example: "Unable to evaluate rule due to a database error: [error message from tool]"
"""

def get_rule_checking_prompt(claim_id: str = None) -> str:
    """Generates the system prompt, optionally scoping it to a specific ClaimID."""
    claim_id_instruction_text = ""
    general_querying_rules_extension_text = "- Use the ClaimID column in a WHERE clause for specific records when a Claim ID is provided."
    if claim_id:
        claim_id_instruction_text = f'CRITICAL INSTRUCTION: You MUST evaluate the current rule ONLY for ClaimID "{claim_id}". All SQL queries MUST include \'WHERE ClaimID = "{claim_id}"\'.'
        general_querying_rules_extension_text = ""
    
    return RULE_CHECKING_PROMPT_TEMPLATE.format(
        claim_id_instruction=claim_id_instruction_text,
        general_querying_rules_extension=general_querying_rules_extension_text
    ).strip()

# Define the SQL tool for Gemini
sql_tool = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name='execute_sql_query',
            description=f"Executes a read-only (SELECT) SQL query against the {TABLE_NAME} table to retrieve claim information. Returns results as a JSON string.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    'sql_query': genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description=f"The SQLite SELECT query for the {TABLE_NAME} table. Columns with special characters MUST be in double quotes."
                    )
                },
                required=['sql_query']
            )
        )
    ]
)

def check_single_rule(rule_text: str, claim_id: str = None) -> str:
    """Processes a single rule using Gemini and returns the textual response."""
    logging.info(f"Checking rule: '{rule_text}' for ClaimID: {claim_id or 'Any'}")
    try:
        genai.configure(api_key=API_KEY)
        
        final_system_prompt = get_rule_checking_prompt(claim_id)
        
        model = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            generation_config=genai.types.GenerationConfig(temperature=0.0),
            safety_settings=[
                {"category": c, "threshold": "BLOCK_NONE"} for c in 
                ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
            ],
            system_instruction=final_system_prompt, 
            tools=[sql_tool]
        )

        chat = model.start_chat(enable_automatic_function_calling=False)
        response = chat.send_message(rule_text)

        if response.parts and response.parts[0].function_call:
            function_call = response.parts[0].function_call
            tool_name = function_call.name
            logging.info(f"Gemini requested function call: {tool_name}")

            if tool_name == 'execute_sql_query':
                args = dict(function_call.args)
                sql_query = args.get('sql_query')
                if not sql_query:
                    return "Error: Gemini requested a database query but the query was missing."
                
                tool_result_json = tooling.execute_sql_query(sql_query)
                
                try:
                    tool_result_data = json.loads(tool_result_json)
                except json.JSONDecodeError as e:
                    return f"Error: Failed to parse tool result: {e}"

                response = chat.send_message(
                    genai.protos.Part(function_response=genai.protos.FunctionResponse(
                        name=tool_name,
                        response={"result": tool_result_data}
                    ))
                )
                return response.text
            else:
                return f"Error: Gemini requested an unknown tool: {tool_name}"
        else:
            return response.text

    except Exception as e:
        logging.exception("Error in check_single_rule:")
        return f"An error occurred while checking the rule: {e}"

def check_rules_from_file(file_content_string: str, claim_id: str = None) -> List[dict]:
    """Processes multiple rules from a file, scoping to a claim_id if provided."""
    rules = [rule.strip() for rule in file_content_string.splitlines() if rule.strip()]
    if not rules:
        return [{'Rule': 'N/A', 'Result': 'No rules found in the file.'}]

    processed_rules = []
    for rule in rules:
        try:
            result = check_single_rule(rule, claim_id)
            processed_rules.append({'Rule': rule, 'Result': result})
        except Exception as e:
            logging.error(f"Error processing rule '{rule}': {e}", exc_info=True)
            processed_rules.append({'Rule': rule, 'Result': f"Error: {e}"})
    
    return processed_rules

def get_sql_from_question_and_schema(question: str, claim_id: str, table_name: str, columns_list: List[str]) -> Optional[str]:
    """
    Generates an SQL query from a natural language question using Gemini,
    constrained by the given table name, columns, and ClaimID.

    Args:
        question: The natural language L1 rule question.
        claim_id: The specific ClaimID to query against.
        table_name: The name of the table to query (e.g., "PatientData").
        columns_list: A list of valid column names for the table.

    Returns:
        A string containing the SQL query, or None if an error occurs.
    """
    logging.info(f"Generating SQL for question: '{question}' for ClaimID: {claim_id}, Table: {table_name}")
    try:
        genai.configure(api_key=API_KEY)
        
        # Prepare the column list string for the prompt
        formatted_columns_str = '\n'.join([f'- "{col}"' for col in columns_list])
        
        # Construct the system prompt for SQL generation
        # This prompt is more direct and doesn't use the complex template formatting of RULE_CHECKING_PROMPT_TEMPLATE
        system_prompt_for_sql_gen = (
            f"You are an AI assistant that translates natural language questions into SQLite SELECT queries.\n"
            f"Your goal is to generate a syntactically correct SQLite SELECT query that will retrieve the answer to the given question from the table '{table_name}', considering the provided columns and the ClaimID '{claim_id}'.\n\n"
            f"Table Schema: '{table_name}'\nColumns:\n{formatted_columns_str}\n\n"
            f"CRITICAL INSTRUCTION: The query MUST include 'WHERE ClaimID = ?'. Your response MUST be ONLY the SQL query string itself. Do not include any explanations or markdown.\n\n"
            f"Question: {question}"
        )

        model = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            generation_config=genai.types.GenerationConfig(temperature=0.0), # Low temperature for deterministic SQL
            safety_settings=[
                {"category": c, "threshold": "BLOCK_NONE"} for c in 
                ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
            ]
            # No system_instruction here, the whole prompt is sent as user message for direct SQL generation
        )

        # For direct SQL generation, we send the entire constructed prompt as the user message.
        # The SQL_GENERATION_PROMPT_TEMPLATE provides the core instructions.
        # We are essentially making a single-turn request for SQL.
        
        full_prompt_for_llm = (
            f"{SQL_GENERATION_PROMPT_TEMPLATE.strip()}\n\n"
            f"Input Details:\n"
            f"Question: \"{question}\"\n"
            f"Table Name: \"{table_name}\"\n"
            f"Columns: {columns_list}\n"
            f"ClaimID: \"{claim_id}\"\n\n"
            f"Generated SQL Query:"
        )
        
        logging.debug(f"Full prompt for SQL generation LLM:\n{full_prompt_for_llm}")
        response = model.generate_content(full_prompt_for_llm)

        if response.text:
            generated_sql = response.text.strip()
            # Basic validation: ensure it's a SELECT query and contains the ClaimID placeholder
            if generated_sql.upper().startswith("SELECT") and "WHERE ClaimID = ?" in generated_sql:
                logging.info(f"Successfully generated SQL: {generated_sql}")
                return generated_sql
            else:
                logging.error(f"Generated text is not a valid SQL query or misses ClaimID placeholder: {generated_sql}")
                return None
        else:
            logging.error("LLM did not return any text for SQL generation.")
            return None

    except Exception as e:
        logging.exception("Error in get_sql_from_question_and_schema:")
        return None