"""
Document submission status checking functionality.
Checks if documents are submitted by verifying non-null values in database columns.
"""
import psycopg2
import logging
import os
import re
from typing import List
from .config import CLAIMS_DB_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_table_column_names(conn: psycopg2.extensions.connection, table_name: str) -> List[str]:
    """Helper function to get column names for a table in PostgreSQL."""
    cursor = conn.cursor()
    try:
        cursor.execute(f"""SELECT column_name FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = '{table_name}';""")
        columns = [row[0] for row in cursor.fetchall()]
        if not columns:
            logging.warning(f"No columns found for table '{table_name}'. It might be empty or not exist as expected.")
        return columns
    except psycopg2.Error as e:
        logging.error(f"Error fetching column names for table '{table_name}': {e}")
        return []


def check_document_submission_status(claim_id: str, document_keyword: str) -> bool:
    """
    Checks if a document, identified by a keyword, is considered submitted for a given ClaimID
    by checking for non-null values in columns that match the keyword in the PatientData table.

    Args:
        claim_id: The ClaimID to check.
        document_keyword: The keyword to identify relevant columns (e.g., "claim form", "Aadhaar card").

    Returns:
        True if at least one relevant column has a non-NULL/non-empty value, False otherwise.
    """
    if not claim_id:
        logging.warning("Claim ID not provided. Cannot check document status.")
        return False
    if not document_keyword:
        logging.warning("Document keyword not provided. Cannot check document status.")
        return False

    match = re.search(r'Is the (.*) submitted\??', document_keyword, re.IGNORECASE)
    core_keyword = match.group(1).strip() if match else document_keyword

    normalized_keyword = core_keyword.lower().replace(" ", "_")
    table_name = "PatientData"
    conn = None

    logging.info(f"Checking document submission for ClaimID: '{claim_id}', Keyword: '{document_keyword}' (Normalized: '{normalized_keyword}')")

    try:
        conn = psycopg2.connect(**CLAIMS_DB_CONFIG)
        cursor = conn.cursor()

        all_column_names = get_table_column_names(conn, table_name)
        if not all_column_names:
            return False

        relevant_columns = [col for col in all_column_names if normalized_keyword in col.lower()]

        if not relevant_columns:
            logging.debug(f"No columns containing keyword '{normalized_keyword}' found in table '{table_name}'.")
            return False
        
        logging.debug(f"Relevant columns in '{table_name}' for keyword '{normalized_keyword}': {relevant_columns}")
        
        select_cols_str = ", ".join([f'"{col}"' for col in relevant_columns])
        query = f'SELECT {select_cols_str} FROM "{table_name}" WHERE claimid = %s'
        
        logging.debug(f"Executing query on {table_name}: {query} with claim_id: {claim_id}")
        cursor.execute(query, (claim_id,))
        row = cursor.fetchone()

        if row:
            for value in row:
                if value is not None and str(value).strip() != "":
                    logging.info(f"Found non-empty value for keyword '{document_keyword}' for ClaimID '{claim_id}'. Document submitted.")
                    return True
        else:
            logging.debug(f"No record found for ClaimID '{claim_id}' in table '{table_name}'.")

    except psycopg2.Error as e:
        logging.error(f"Database error while checking document status for ClaimID '{claim_id}', keyword '{document_keyword}': {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred for ClaimID '{claim_id}', keyword '{document_keyword}': {e}")
        return False
    finally:
        if conn:
            conn.close()

    logging.info(f"No non-empty values found for keyword '{document_keyword}' for ClaimID '{claim_id}'. Document considered NOT submitted.")
    return False
