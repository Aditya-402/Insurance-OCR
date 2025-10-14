import sqlite3
import re
import os
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(__file__), 'rules.db')
RULES_FILE_PATH = os.path.join(os.path.dirname(__file__), 'rules_base.txt')

def get_document_name_from_check_rule(rule_text):
    """Extracts document name from a check rule.
    Example: 'Is the claim form submitted?' -> 'claim form'
    """
    match = re.search(r'Is the (.*?) submitted\?', rule_text)
    if match:
        return match.group(1).strip().lower()
    return None

def create_connection(db_file):
    """Create a database connection to the SQLite database specified by db_file"""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def create_table(conn, create_table_sql):
    """Create a table from the create_table_sql statement"""
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")

def main():
    # --- Database Setup ---
    conn = create_connection(DB_PATH)
    if not conn:
        return

    # Drop tables if they exist to ensure a fresh start
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS L1_Rules") # Drop dependent table first
    cursor.execute("DROP TABLE IF EXISTS Check_Rules")
    cursor.execute("DROP TABLE IF EXISTS L2_Rules")
    conn.commit()

    # --- Table Creation ---
    sql_create_check_rules_table = """
    CREATE TABLE IF NOT EXISTS Check_Rules (
        rule_id TEXT PRIMARY KEY,
        rule_description TEXT NOT NULL
    );
    """
    sql_create_l1_rules_table = """
    CREATE TABLE IF NOT EXISTS L1_Rules (
        rule_id TEXT PRIMARY KEY,
        rule_description TEXT NOT NULL,
        check_rule_id TEXT NOT NULL,
        FOREIGN KEY (check_rule_id) REFERENCES Check_Rules (rule_id)
    );
    """
    sql_create_l2_rules_table = """
    CREATE TABLE IF NOT EXISTS L2_Rules (
        rule_id TEXT PRIMARY KEY,
        rule_description TEXT NOT NULL
    );
    """
    create_table(conn, sql_create_check_rules_table)
    create_table(conn, sql_create_l1_rules_table)
    create_table(conn, sql_create_l2_rules_table)

    # --- Data Population ---
    check_rules_data = []
    l1_rules_data = []
    l2_rules_data = []

    check_rule_doc_map = {} # Stores "document name": "CHXX"

    current_section = None
    ch_counter = 1
    l1_counters = defaultdict(lambda: 1) # To generate L1_XX_YY (YY part)
    l2_counter = 1

    try:
        with open(RULES_FILE_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: {RULES_FILE_PATH} not found.")
        if conn:
            conn.close()
        return

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.lower() == "**check rules**":
            current_section = "check"
            continue
        elif line.lower() == "**l1 rules**":
            current_section = "l1"
            continue
        elif line.lower() == "**l2 rules**":
            current_section = "l2"
            continue

        if current_section == "check":
            rule_id_num = ch_counter
            rule_id_str = f"CH{rule_id_num:02d}"
            doc_name = get_document_name_from_check_rule(line)
            if doc_name:
                check_rules_data.append((rule_id_str, line))
                check_rule_doc_map[doc_name] = rule_id_str
                # rule_id_num is still useful for ch_counter
                ch_counter += 1
            else:
                print(f"Warning: Could not parse document name from check rule: {line}")

        elif current_section == "l1":
            match_docs = re.search(r'on the (.*?)(?:\?|$)', line, re.IGNORECASE)
            associated_check_rule_id = None
            # associated_doc_map_id_for_l1 will be derived from associated_check_rule_id

            if match_docs:
                doc_references_str = match_docs.group(1).strip()
                possible_doc_names = [name.strip().lower() for name in doc_references_str.split('/')]

                for pdn in possible_doc_names:
                    if pdn in check_rule_doc_map:
                        associated_check_rule_id = check_rule_doc_map[pdn]
                        break
                    else:
                        # Attempt partial match for cases like 'aadhaar card' vs 'the aadhaar card'
                        for known_doc, ch_id in check_rule_doc_map.items():
                            if pdn.endswith(known_doc) or known_doc.endswith(pdn):
                                associated_check_rule_id = ch_id
                                break
                        if associated_check_rule_id: # Found via partial match
                            break
            
            if not associated_check_rule_id:
                 # Fallback for L1 rules where 'on the' might not be standard or missing
                 # Try to find any known document name in the rule description
                 for known_doc_name_key in check_rule_doc_map.keys():
                     if known_doc_name_key in line.lower():
                        associated_check_rule_id = check_rule_doc_map[known_doc_name_key]
                        # print(f"Fallback match for L1: '{line}' matched with '{known_doc_name_key}'")
                        break # Take the first one found

            if associated_check_rule_id:
                # Extract numeric part from associated_check_rule_id (e.g., 'CH01' -> 1)
                match_num = re.search(r'\d+', associated_check_rule_id)
                if match_num:
                    doc_map_id_for_l1 = int(match_num.group(0))
                    l1_specific_counter = l1_counters[doc_map_id_for_l1]
                    l1_rule_id = f"L1_{doc_map_id_for_l1:02d}_{l1_specific_counter:02d}"
                    l1_rules_data.append((l1_rule_id, line, associated_check_rule_id))
                    l1_counters[doc_map_id_for_l1] += 1
                else:
                    print(f"Warning: Could not extract numeric ID from check_rule_id '{associated_check_rule_id}' for L1 rule: {line}")
            else:
                print(f"Warning: L1 rule could not be associated with a document and was skipped: {line}")

        elif current_section == "l2":
            rule_id_str = f"L2_{l2_counter:02d}"
            l2_rules_data.append((rule_id_str, line))
            l2_counter += 1

    # --- Insert Data into Tables ---
    cursor = conn.cursor()
    try:
        if check_rules_data:
            cursor.executemany("INSERT INTO Check_Rules (rule_id, rule_description) VALUES (?, ?)", check_rules_data)
        if l1_rules_data:
            cursor.executemany("INSERT INTO L1_Rules (rule_id, rule_description, check_rule_id) VALUES (?, ?, ?)", l1_rules_data)
        if l2_rules_data:
            cursor.executemany("INSERT INTO L2_Rules (rule_id, rule_description) VALUES (?, ?)", l2_rules_data)
        conn.commit()
        print(f"Database '{os.path.basename(DB_PATH)}' created and populated successfully in '{os.path.dirname(DB_PATH)}'.")
        print(f"{len(check_rules_data)} check rules, {len(l1_rules_data)} L1 rules, {len(l2_rules_data)} L2 rules added.")
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()
