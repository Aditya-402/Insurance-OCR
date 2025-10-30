"""
SQL queries for fetching rule-related data from databases.
Includes procedures, check rules, L1 rules, and L2 rules.
"""
import sqlite3
import logging
from typing import List, Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def fetch_all_procedure_names_from_db(db_path: str) -> List[str]:
    """
    Connects to the specified database and fetches all procedure names
    from the Procedure_rules table.

    Args:
        db_path: The path to the SQLite database file.

    Returns:
        A list of procedure names (str).
        Returns an empty list if an error occurs.
    """
    procedure_names = []
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT Proc_Name FROM Procedure_rules ORDER BY Proc_Name")
        rows = cursor.fetchall()
        procedure_names = [row[0] for row in rows]
        logging.info(f"Successfully fetched {len(procedure_names)} procedure names from {db_path}.")
    except sqlite3.Error as e:
        logging.error(f"Database error at {db_path} while fetching procedure names: {e}")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred with {db_path} fetching procedure names: {e}")
        return []
    finally:
        if conn:
            conn.close()
    return procedure_names


def fetch_rules_for_procedure_from_db(db_path: str, procedure_name: str) -> Optional[str]:
    """
    Connects to the specified database and fetches the 'Check_Rules' content
    for a given procedure name from the Procedure_rules table.

    Args:
        db_path: The path to the SQLite database file.
        procedure_name: The name of the procedure to fetch rules for.

    Returns:
        The 'Check_Rules' content as a string, or None if not found or an error occurs.
    """
    rules_content = None
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT Check_Rules FROM Procedure_rules WHERE Proc_Name = ?", (procedure_name,))
        row = cursor.fetchone()
        if row:
            rules_content = row[0]
            logging.info(f"Successfully fetched rules for procedure '{procedure_name}' from {db_path}.")
        else:
            logging.warning(f"No rules found for procedure '{procedure_name}' in {db_path}.")
    except sqlite3.Error as e:
        logging.error(f"Database error at {db_path} while fetching rules for '{procedure_name}': {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred with {db_path} fetching rules for '{procedure_name}': {e}")
        return None
    finally:
        if conn:
            conn.close()
    return rules_content


def fetch_rule_descriptions_for_ids_from_db(db_path: str, rule_ids: List[str]) -> dict[str, str]:
    """
    Connects to the specified database and fetches the 'Rule_Description' for a list of 'Rule_ID's
    from the 'Check_Rules' table.

    Args:
        db_path: The path to the SQLite database file.
        rule_ids: A list of Rule_ID strings to fetch descriptions for.

    Returns:
        A dictionary mapping Rule_ID to its Rule_Description.
        If a Rule_ID is not found, it won't be included in the dictionary.
        Returns an empty dictionary if an error occurs or no IDs are provided.
    """
    if not rule_ids:
        return {}

    descriptions = {}
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Prepare a query with placeholders for the IN clause
        placeholders = ','.join(['?'] * len(rule_ids))
        query = f"SELECT Rules_ID, Rules_description FROM Check_Rules WHERE Rules_ID IN ({placeholders})"
        
        cursor.execute(query, rule_ids)
        rows = cursor.fetchall()
        
        for row in rows:
            descriptions[row[0]] = row[1]
            
        logging.info(f"Successfully fetched descriptions for {len(descriptions)} rule IDs from {db_path}.")
        
        # Log any IDs for which descriptions were not found
        found_ids = set(descriptions.keys())
        not_found_ids = [rid for rid in rule_ids if rid not in found_ids]
        if not_found_ids:
            logging.warning(f"No descriptions found for Rule_IDs: {', '.join(not_found_ids)} in {db_path}.")
            
    except sqlite3.Error as e:
        logging.error(f"Database error at {db_path} while fetching rule descriptions: {e}")
        return {}
    except Exception as e:
        logging.error(f"An unexpected error occurred with {db_path} fetching rule descriptions: {e}")
        return {}
    finally:
        if conn:
            conn.close()
    return descriptions


def fetch_procedure_rules_expression_from_db(db_path: str, procedure_name: str) -> Optional[str]:
    """
    Connects to the specified database and fetches the 'procedure_rules' expression string
    for a given procedure name from the Procedure_rules table.

    Args:
        db_path: The path to the SQLite database file.
        procedure_name: The name of the procedure to fetch the expression for.

    Returns:
        The 'procedure_rules' content as a string, or None if not found or an error occurs.
    """
    expression_content = None
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT procedure_rules FROM Procedure_rules WHERE Proc_Name = ?", (procedure_name,))
        row = cursor.fetchone()
        if row:
            expression_content = row[0]
            logging.info(f"Successfully fetched procedure rules expression for '{procedure_name}' from {db_path}.")
        else:
            logging.warning(f"No procedure rules expression found for procedure '{procedure_name}' in {db_path}.")
    except sqlite3.Error as e:
        logging.error(f"Database error at {db_path} while fetching procedure rules expression for '{procedure_name}': {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred with {db_path} fetching procedure rules expression for '{procedure_name}': {e}")
        return None
    finally:
        if conn:
            conn.close()
    return expression_content


def fetch_parent_check_rule_id(db_path: str, l1_rule_id: str) -> Optional[str]:
    """
    Connects to the rules database and fetches the parent 'check_rule_id' for a given 'l1_rule_id'.

    Args:
        db_path: The path to the SQLite database file.
        l1_rule_id: The L1 rule ID to look up.

    Returns:
        The parent 'check_rule_id' as a string, or None if not found or an error occurs.
    """
    parent_id = None
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT check_rule_id FROM L1_Rules WHERE rule_id = ?", (l1_rule_id,))
        row = cursor.fetchone()
        if row:
            parent_id = row[0]
        else:
            logging.warning(f"No parent check_rule_id found for L1 rule '{l1_rule_id}' in {db_path}.")
    except sqlite3.Error as e:
        logging.error(f"Database error at {db_path} while fetching parent for '{l1_rule_id}': {e}")
        return None
    finally:
        if conn:
            conn.close()
    return parent_id


def fetch_all_l2_rules_from_db(db_path: str) -> List[Dict[str, Any]]:
    """
    Connects to the database and fetches all L2 rules.

    Args:
        db_path: The path to the SQLite database file.

    Returns:
        A list of dictionaries, where each dictionary represents an L2 rule
        with its 'rule_id' and 'description'.
        Returns an empty list if no rules are found or an error occurs.
    """
    l2_rules = []
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        query = "SELECT rule_id, rule_description, L1_rule_id FROM L2_Rules"
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            l2_rules.append({
                'rule_id': row[0],
                'description': row[1],
                'l1_data_references': row[2]
            })
        logging.info(f"Successfully fetched {len(l2_rules)} L2 rules from the database.")
    except sqlite3.Error as e:
        logging.error(f"Database error fetching L2 rules: {e}")
        return []
    finally:
        if conn:
            conn.close()
    return l2_rules


def fetch_l1_rule_descriptions(rules_db_path: str, check_rule_id: str) -> List[str]:
    """
    Fetches all L1 rule descriptions for a given check_rule_id.

    Args:
        rules_db_path: Path to the rules SQLite database.
        check_rule_id: The parent check_rule_id to fetch L1 rules for.

    Returns:
        A list of L1 rule description strings.
    """
    descriptions = []
    conn = None
    try:
        conn = sqlite3.connect(rules_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT description FROM L1_Rules WHERE check_rule_id = ?", (check_rule_id,))
        rows = cursor.fetchall()
        descriptions = [row[0] for row in rows]
    except sqlite3.Error as e:
        logging.error(f"Database error fetching L1 descriptions for {check_rule_id}: {e}")
    finally:
        if conn:
            conn.close()
    return descriptions


def fetch_l1_rule_descriptions_with_values(rules_db_path: str, check_rule_id: str, claims_db_path: str, claim_id: str) -> List[Dict[str, Any]]:
    """
    Fetches L1 rule descriptions and executes their SQL queries for a given check_rule_id and claim_id.

    Args:
        rules_db_path: Path to the rules SQLite database.
        check_rule_id: The Rule_ID from the Check_Rules table to link to L1_Rules.
        claims_db_path: Path to the claims database.
        claim_id: The ClaimID to use for query substitution.

    Returns:
        A list of dicts: { 'rule_id': ..., 'description': ..., 'value': ... }
    """
    results = []
    conn_rules = None
    try:
        conn_rules = sqlite3.connect(rules_db_path)
        cursor_rules = conn_rules.cursor()
        query = "SELECT Rule_ID, Rule_Description, sql_query FROM L1_Rules WHERE check_rule_id = ?"
        cursor_rules.execute(query, (check_rule_id,))
        rows = cursor_rules.fetchall()
        for rule_id, desc, sql_query in rows:
            value = None
            if sql_query:
                try:
                    with sqlite3.connect(claims_db_path) as conn_claims:
                        cursor_claims = conn_claims.cursor()
                        # Use parameterized query for security and correctness
                        if '?' in sql_query:
                            cursor_claims.execute(sql_query, (claim_id,))
                        else:
                            # Execute queries that don't need a claim_id (if any)
                            cursor_claims.execute(sql_query)
                        
                        val_row = cursor_claims.fetchone()
                        if val_row is not None:
                            value = val_row[0] if len(val_row) == 1 else val_row
                        else:
                            value = "N/A" # Explicitly set value if no result is found
                except Exception as e:
                    value = f"Error executing SQL: {e}"
            results.append({'rule_id': rule_id, 'description': desc, 'value': value})
    except sqlite3.Error as e:
        logging.error(f"SQLite error fetching L1 rules for '{check_rule_id}' from {rules_db_path}: {e}")
    except Exception as e:
        logging.error(f"Unhandled error in fetch_l1_rule_descriptions_with_values: {e}")
    finally:
        if conn_rules:
            conn_rules.close()
    return results
    

def _fetch_data_for_l1_rule(rule_id: str, rules_db_path: str, claims_db_path: str, claim_id: str) -> str:
    """Fetches the SQL query for an L1 rule, executes it, and returns the value."""
    try:
        # Get SQL query from rules.db
        with sqlite3.connect(rules_db_path) as rules_conn:
            cursor = rules_conn.cursor()
            cursor.execute("SELECT sql_query FROM L1_Rules WHERE Rule_ID = ?", (rule_id,))
            result = cursor.fetchone()
            if not result:
                return f"Error: L1_Rule '{rule_id}' not found."
            sql_query = result[0]

        # Execute query on claims.db
        with sqlite3.connect(claims_db_path) as claims_conn:
            cursor = claims_conn.cursor()
            if '?' in sql_query:
                cursor.execute(sql_query, (claim_id,))
            else:
                cursor.execute(sql_query)
            value_result = cursor.fetchone()
            return str(value_result[0]) if value_result else "N/A"
    except Exception as e:
        logging.error(f"DB error fetching data for rule {rule_id}: {e}")
        return f"Error fetching data: {e}"
