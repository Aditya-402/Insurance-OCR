"""
Document submission status checking functionality.
Checks if documents are submitted by verifying non-null values in database columns.
"""
import sqlite3
import logging
import os
import re
from typing import List
from config import DB_PATH as CLAIMS_DB_PATH

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_table_column_names(conn: sqlite3.Connection, table_name: str) -> List[str]:
    """Helper function to get column names for a table."""
    cursor = conn.cursor()
    try:
        cursor.execute(f"PRAGMA table_info('{table_name}');")
        columns = [row[1] for row in cursor.fetchall()]
        if not columns:
            logging.warning(f"No columns found for table '{table_name}'. It might be empty or not exist as expected.")
        return columns
    except sqlite3.Error as e:
        logging.error(f"Error fetching column names for table '{table_name}': {e}")
        return []


def check_document_submission_status(claim_id: str, document_keyword: str, db_path: str = CLAIMS_DB_PATH) -> bool:
    """
    Checks if a document, identified by a keyword, is considered submitted for a given ClaimID
    It checks for non-null values in columns that match the keyword in the 
    PatientData table.

    Args:
        claim_id: The ClaimID to check.
        document_keyword: The keyword to identify relevant columns (e.g., "claim form", "Aadhaar card").
                          This will be normalized (lowercase, spaces to underscores).
        db_path: Path to the claims_database.db.

    Returns:
        True if at least one relevant column has a non-NULL/non-empty value, False otherwise.
    """
    if not os.path.exists(db_path):
        logging.error(f"Claims database not found at: {db_path}. Cannot check document status for ClaimID '{claim_id}'.")
        return False
    if not claim_id:
        logging.warning("Claim ID not provided. Cannot check document status.")
        return False
    if not document_keyword:
        logging.warning("Document keyword not provided. Cannot check document status.")
        return False

    # Try to extract the core document name from the description.
    # e.g., from "Is the claim form submitted?", extract "claim form".
    match = re.search(r'Is the (.*) submitted\??', document_keyword, re.IGNORECASE)
    if match:
        core_keyword = match.group(1).strip()
    else:
        # Fallback to using the whole keyword if the pattern doesn't match
        core_keyword = document_keyword

    normalized_keyword = core_keyword.lower().replace(" ", "_")
    # As per request, check only the PatientData table for the document
    tables_to_check = ["PatientData"]
    conn = None

    logging.info(f"Checking document submission for ClaimID: '{claim_id}', Keyword: '{document_keyword}' (Normalized: '{normalized_keyword}')")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for table_name in tables_to_check:
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            if not cursor.fetchone():
                logging.warning(f"Table '{table_name}' does not exist in {db_path}. Skipping.")
                continue

            all_column_names = get_table_column_names(conn, table_name)
            if not all_column_names:
                # get_table_column_names already logs a warning
                continue

            relevant_columns = [
                col for col in all_column_names 
                if normalized_keyword in col.lower()
            ]

            if not relevant_columns:
                logging.debug(f"No columns containing keyword '{normalized_keyword}' found in table '{table_name}'.")
                continue
            
            logging.debug(f"Relevant columns in '{table_name}' for keyword '{normalized_keyword}': {relevant_columns}")
            
            select_cols_str = ", ".join([f'"{col}"' for col in relevant_columns])
            # Assuming 'claimid' is the standard column name for Claim ID
            query = f'SELECT {select_cols_str} FROM "{table_name}" WHERE claimid = ?'
            
            logging.debug(f"Executing query on {table_name}: {query} with claim_id: {claim_id}")
            cursor.execute(query, (claim_id,))
            row = cursor.fetchone()

            if row:
                for value in row:
                    if value is not None and str(value).strip() != "":
                        logging.info(f"Found non-empty value for keyword '{document_keyword}' in table '{table_name}' for ClaimID '{claim_id}'. Document considered submitted.")
                        return True
            else:
                logging.debug(f"No record found for ClaimID '{claim_id}' in table '{table_name}'.")

    except sqlite3.Error as e:
        logging.error(f"Database error at {db_path} while checking document status for ClaimID '{claim_id}', keyword '{document_keyword}': {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred with {db_path} for ClaimID '{claim_id}', keyword '{document_keyword}': {e}")
        return False
    finally:
        if conn:
            conn.close()

    logging.info(f"No non-empty values found for keyword '{document_keyword}' for ClaimID '{claim_id}'. Document considered NOT submitted.")
    return False
