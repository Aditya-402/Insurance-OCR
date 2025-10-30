"""
SQL queries for fetching rule-related data from databases.
Includes procedures, check rules, L1 rules, and L2 rules.
"""
import psycopg2
import logging
from typing import List, Optional, Dict, Any
from .config import RULES_DB_CONFIG, CLAIMS_DB_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def fetch_all_procedure_names_from_db() -> List[str]:
    """
    Connects to the PostgreSQL database and fetches all procedure names
    from the Procedure_rules table.
    """
    procedure_names = []
    conn = None
    try:
        conn = psycopg2.connect(**RULES_DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute('SELECT proc_name FROM procedure_rules ORDER BY proc_name')
        rows = cursor.fetchall()
        procedure_names = [row[0] for row in rows]
        logging.info(f"Successfully fetched {len(procedure_names)} procedure names.")
    except psycopg2.Error as e:
        logging.error(f"Database error while fetching procedure names: {e}")
        return []
    finally:
        if conn:
            conn.close()
    return procedure_names


def fetch_rules_for_procedure_from_db(procedure_name: str) -> Optional[str]:
    """
    Connects to the PostgreSQL database and fetches the 'Check_Rules' content
    for a given procedure name from the Procedure_rules table.
    """
    rules_content = None
    conn = None
    try:
        conn = psycopg2.connect(**RULES_DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute('SELECT check_rules FROM procedure_rules WHERE proc_name = %s', (procedure_name,))
        row = cursor.fetchone()
        if row:
            rules_content = row[0]
            logging.info(f"Successfully fetched rules for procedure '{procedure_name}'.")
        else:
            logging.warning(f"No rules found for procedure '{procedure_name}'.")
    except psycopg2.Error as e:
        logging.error(f"Database error while fetching rules for '{procedure_name}': {e}")
        return None
    finally:
        if conn:
            conn.close()
    return rules_content


def fetch_rule_descriptions_for_ids_from_db(rule_ids: List[str]) -> Dict[str, str]:
    """
    Connects to the PostgreSQL database and fetches the 'Rule_Description' for a list of 'Rule_ID's
    from the 'Check_Rules' table.
    """
    if not rule_ids:
        return {}

    descriptions = {}
    conn = None
    try:
        conn = psycopg2.connect(**RULES_DB_CONFIG)
        cursor = conn.cursor()
        
        placeholders = ','.join(['%s'] * len(rule_ids))
        query = f'SELECT rules_id, rules_description FROM check_rules WHERE rules_id IN ({placeholders})'
        
        cursor.execute(query, rule_ids)
        rows = cursor.fetchall()
        
        for row in rows:
            descriptions[row[0]] = row[1]
            
        logging.info(f"Successfully fetched descriptions for {len(descriptions)} rule IDs.")
        
        found_ids = set(descriptions.keys())
        missing_ids = set(rule_ids) - found_ids
        if missing_ids:
            logging.warning(f"Could not find descriptions for the following rule IDs: {missing_ids}")
            
    except psycopg2.Error as e:
        logging.error(f"Database error while fetching rule descriptions: {e}")
        return {}
    finally:
        if conn:
            conn.close()
            
    return descriptions


def fetch_procedure_rules_expression_from_db(procedure_name: str) -> Optional[str]:
    """
    Connects to the PostgreSQL database and fetches the 'procedure_rules' expression string
    for a given procedure name from the Procedure_rules table.
    """
    expression_content = None
    conn = None
    try:
        conn = psycopg2.connect(**RULES_DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute('SELECT procedure_rules FROM procedure_rules WHERE proc_name = %s', (procedure_name,))
        row = cursor.fetchone()
        if row:
            expression_content = row[0]
            logging.info(f"Successfully fetched procedure rules expression for '{procedure_name}'.")
        else:
            logging.warning(f"No procedure rules expression found for procedure '{procedure_name}'.")
    except psycopg2.Error as e:
        logging.error(f"Database error while fetching procedure rules expression for '{procedure_name}': {e}")
        return None
    finally:
        if conn:
            conn.close()
    return expression_content


def fetch_parent_check_rule_id(l1_rule_id: str) -> Optional[str]:
    """
    Connects to the rules database and fetches the parent 'check_rule_id' for a given 'l1_rule_id'.
    """
    parent_id = None
    conn = None
    try:
        conn = psycopg2.connect(**RULES_DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute('SELECT check_rule_id FROM l1_rules WHERE rule_id = %s', (l1_rule_id,))
        row = cursor.fetchone()
        if row:
            parent_id = row[0]
        else:
            logging.warning(f"No parent check_rule_id found for L1 rule '{l1_rule_id}'.")
    except psycopg2.Error as e:
        logging.error(f"Database error while fetching parent for '{l1_rule_id}': {e}")
        return None
    finally:
        if conn:
            conn.close()
    return parent_id


def fetch_all_l2_rules_from_db() -> List[Dict[str, Any]]:
    """
    Connects to the database and fetches all L2 rules.
    """
    l2_rules = []
    conn = None
    try:
        conn = psycopg2.connect(**RULES_DB_CONFIG)
        cursor = conn.cursor()
        query = 'SELECT rule_id, rule_description, l1_rule_id FROM l2_rules'
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            l2_rules.append({
                'rule_id': row[0],
                'description': row[1],
                'l1_data_references': row[2]
            })
        logging.info(f"Successfully fetched {len(l2_rules)} L2 rules from the database.")
    except psycopg2.Error as e:
        logging.error(f"Database error fetching L2 rules: {e}")
        return []
    finally:
        if conn:
            conn.close()
    return l2_rules


def fetch_l1_rule_descriptions(check_rule_id: str) -> List[str]:
    """
    Fetches L1 rule descriptions for a given check_rule_id.
    """
    descriptions = []
    conn = None
    try:
        conn = psycopg2.connect(**RULES_DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute('SELECT rule_description FROM l1_rules WHERE check_rule_id = %s', (check_rule_id,))
        rows = cursor.fetchall()
        descriptions = [row[0] for row in rows]
    except psycopg2.Error as e:
        logging.error(f"Database error fetching L1 descriptions for {check_rule_id}: {e}")
    finally:
        if conn:
            conn.close()
    return descriptions


def fetch_l1_rule_descriptions_with_values(check_rule_id: str, claim_id: str) -> List[Dict[str, str]]:
    """
    Fetches L1 rule descriptions and their corresponding values from the claims database.
    """
    results = []
    conn_rules = None
    try:
        conn_rules = psycopg2.connect(**RULES_DB_CONFIG)
        cursor_rules = conn_rules.cursor()
        query = 'SELECT rule_id, rule_description, sql_query FROM l1_rules WHERE check_rule_id = %s'
        cursor_rules.execute(query, (check_rule_id,))
        rows = cursor_rules.fetchall()
        for rule_id, rule_description, sql_query in rows:
            value = None
            if sql_query:
                try:
                    with psycopg2.connect(**CLAIMS_DB_CONFIG) as conn_claims:
                        cursor_claims = conn_claims.cursor()
                        final_query = sql_query.replace('?', '%s')
                        if '%s' in final_query:
                            cursor_claims.execute(final_query, (claim_id,))
                        else:
                            cursor_claims.execute(final_query)
                        
                        val_row = cursor_claims.fetchone()
                        if val_row is not None:
                            value = val_row[0] if len(val_row) == 1 else val_row
                        else:
                            value = "N/A"
                except Exception as e:
                    value = f"Error executing SQL: {e}"
            results.append({'description': rule_description, 'value': value})
    except psycopg2.Error as e:
        logging.error(f"PostgreSQL error fetching L1 rules for '{check_rule_id}': {e}")
    finally:
        if conn_rules:
            conn_rules.close()
    return results

def _fetch_data_for_l1_rule(rule_id: str, claim_id: str) -> str:
    """Fetches the SQL query for an L1 rule, executes it, and returns the value."""
    try:
        with psycopg2.connect(**RULES_DB_CONFIG) as rules_conn:
            cursor = rules_conn.cursor()
            cursor.execute('SELECT sql_query FROM l1_rules WHERE rule_id = %s', (rule_id,))
            result = cursor.fetchone()
            if not result:
                return f"Error: L1_Rule '{rule_id}' not found."
            sql_query = result[0]

        with psycopg2.connect(**CLAIMS_DB_CONFIG) as claims_conn:
            cursor = claims_conn.cursor()
            final_query = sql_query.replace('?', '%s')
            if '%s' in final_query:
                cursor.execute(final_query, (claim_id,))
            else:
                cursor.execute(final_query)
            value_result = cursor.fetchone()
            return str(value_result[0]) if value_result else "N/A"
    except Exception as e:
        logging.error(f"DB error fetching data for rule {rule_id}: {e}")
        return f"Error fetching data: {e}"
