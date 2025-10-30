import psycopg2
import sys
import os

# Add project root to path to allow for sibling imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from check_rules.config import RULES_DB_CONFIG

def update_day_care_rule():
    """
    Connects to the Rules database and updates the 'procedure_rules' for the 'Day Care' procedure.
    """
    conn = None
    try:
        conn = psycopg2.connect(**RULES_DB_CONFIG)
        cursor = conn.cursor()
        
        procedure_name = 'A V Fistula For Dialysis (Day Care)'
        new_expression = '[]'
        
        # Update the procedure_rules column for the specified procedure
        query = 'UPDATE procedure_rules SET check_rules = %s WHERE proc_name = %s;'
        
        cursor.execute(query, (new_expression, procedure_name))
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"Successfully updated the rule for '{procedure_name}'.")
        else:
            print(f"Could not find the procedure '{procedure_name}' to update.")
            
    except psycopg2.Error as e:
        print(f"Database Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_day_care_rule()
