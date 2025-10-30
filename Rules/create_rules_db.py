import psycopg2
import pandas as pd
import os
from sqlalchemy import create_engine

# Assuming check_rules is in the parent directory, adjust if necessary
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from check_rules.config import RULES_DB_CONFIG

# --- Configuration ---
EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'rules.xlsx')

def create_connection():
    """Create a database connection to the PostgreSQL database."""
    try:
        return psycopg2.connect(**RULES_DB_CONFIG)
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def create_table(conn, create_table_sql):
    """Create a table from the create_table_sql statement."""
    try:
        with conn.cursor() as c:
            c.execute(create_table_sql)
        conn.commit()
    except psycopg2.Error as e:
        print(f"Error creating table: {e}")
        conn.rollback()

def main():
    # --- Database Setup ---
    conn = create_connection()
    if not conn:
        return

    print(f"Database connection established to {RULES_DB_CONFIG['dbname']}")

    # --- Table Definitions ---
    sql_create_procedure_rules_table = """ CREATE TABLE IF NOT EXISTS procedure_rules (
                                        id SERIAL PRIMARY KEY,
                                        proc_name TEXT NOT NULL,
                                        check_rules TEXT,
                                        procedure_rules TEXT
                                    ); """

    sql_create_check_rules_table = """CREATE TABLE IF NOT EXISTS check_rules (
                                    rules_id TEXT PRIMARY KEY,
                                    rules_description TEXT NOT NULL
                                );"""

    sql_create_l1_rules_table = """CREATE TABLE IF NOT EXISTS l1_rules (
                                    rule_id TEXT PRIMARY KEY,
                                    check_rule_id TEXT,
                                    description TEXT NOT NULL,
                                    sql_query TEXT,
                                    FOREIGN KEY (check_rule_id) REFERENCES check_rules (rules_id)
                                );"""

    sql_create_l2_rules_table = """CREATE TABLE IF NOT EXISTS l2_rules (
                                    rule_id TEXT PRIMARY KEY,
                                    rule_description TEXT NOT NULL,
                                    l1_rule_id TEXT,
                                    FOREIGN KEY (l1_rule_id) REFERENCES l1_rules (rule_id)
                                );"""

    # --- Table Creation ---
    create_table(conn, sql_create_procedure_rules_table)
    create_table(conn, sql_create_check_rules_table)
    create_table(conn, sql_create_l1_rules_table)
    create_table(conn, sql_create_l2_rules_table)

    # --- Data Population ---
    try:
        df_proc = pd.read_excel(EXCEL_PATH, sheet_name='Procedure_rules')
        df_check = pd.read_excel(EXCEL_PATH, sheet_name='Check_Rules')
        df_l1 = pd.read_excel(EXCEL_PATH, sheet_name='L1_Rules')
        df_l2 = pd.read_excel(EXCEL_PATH, sheet_name='L2_Rules')

    except FileNotFoundError:
        print(f"Error: The file {EXCEL_PATH} was not found.")
        conn.close()
        return
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        conn.close()
        return

    # --- Data Cleaning and Validation ---
    # Standardize all column names to lowercase to prevent case-sensitivity issues
    df_proc.columns = [col.lower() for col in df_proc.columns]
    df_check.columns = [col.lower() for col in df_check.columns]
    df_l1.columns = [col.lower() for col in df_l1.columns]
    df_l2.columns = [col.lower() for col in df_l2.columns]

    # Validate and clean 'check_rules' column in the procedure rules DataFrame
    if 'check_rules' in df_proc.columns:
        # Replace non-expression values (like 'Day Care') with a valid empty expression '[]'
        df_proc['check_rules'] = df_proc['check_rules'].apply(
            lambda x: x if isinstance(x, str) and (x.strip().startswith('[') or x.strip().startswith('(')) else '[]'
        )
        print("Validated and cleaned 'check_rules' column.")

    # Insert data into tables using SQLAlchemy for robust DataFrame handling
    try:
        db_user = RULES_DB_CONFIG['user']
        db_password = RULES_DB_CONFIG['password']
        db_host = RULES_DB_CONFIG['host']
        db_port = RULES_DB_CONFIG['port']
        db_name = RULES_DB_CONFIG['dbname']
        engine_str = f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
        engine = create_engine(engine_str)

        # Use a temporary connection from the engine to insert data
        with engine.connect() as temp_conn:
            df_proc.to_sql('procedure_rules', temp_conn, if_exists='replace', index=False)
            df_check.to_sql('check_rules', temp_conn, if_exists='replace', index=False)
            df_l1.to_sql('l1_rules', temp_conn, if_exists='replace', index=False)
            df_l2.to_sql('l2_rules', temp_conn, if_exists='replace', index=False)
        
        print("Data inserted successfully from Excel into the database.")
    except Exception as e:
        print(f"Error inserting data into database: {e}")
    finally:
        conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    main()
