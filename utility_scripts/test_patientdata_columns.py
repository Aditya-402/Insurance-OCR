import psycopg2
import sys
import os

# Add project root to path to allow for sibling imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from check_rules.config import CLAIMS_DB_CONFIG

def get_patientdata_columns():
    """
    Connects to the claims_database and prints the column names of the patientdata table.
    """
    conn = None
    try:
        conn = psycopg2.connect(**CLAIMS_DB_CONFIG)
        cursor = conn.cursor()
        
        table_name = 'PatientData'
        
        # Query to get column names for the specified table
        query = f"""SELECT column_name FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = '{table_name}';"""
                   
        cursor.execute(query)
        columns = cursor.fetchall()
        
        if columns:
            print(f"--- Columns in '{table_name}' table ---")
            for col in columns:
                print(f"- {col[0]}")
            print("-------------------------------------")
        else:
            print(f"Table '{table_name}' not found or it has no columns.")
            
    except psycopg2.Error as e:
        print(f"Database Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    get_patientdata_columns()
