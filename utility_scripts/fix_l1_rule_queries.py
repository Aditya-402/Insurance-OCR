import sqlite3
import os

# This script updates the L1_Rules table in the rules.db to ensure
# that all SQL queries are correctly filtered by ClaimID.

def fix_l1_rule_queries():
    """
    Connects to the rules.db and updates the sql_query in the L1_Rules table
    to include a 'WHERE ClaimID = ?' clause if it's missing.
    """
    # Construct the path to the database file relative to the script's location
    script_dir = os.path.dirname(__file__)
    db_path = os.path.join(script_dir, '..', 'databases', 'rules.db')

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    print(f"Connecting to database at: {db_path}")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch all L1 rules
        cursor.execute("SELECT Rule_ID, sql_query FROM L1_Rules")
        rows = cursor.fetchall()

        rules_to_update = []
        print("\n--- Analyzing L1 Rule Queries ---")
        for rule_id, sql_query in rows:
            if not sql_query:
                print(f"- [SKIP] Rule '{rule_id}' has no SQL query.")
                continue

            clean_query = sql_query.strip()
            if clean_query and not clean_query.endswith(';'):
                new_query = f"{clean_query};"
                rules_to_update.append((new_query, rule_id))
                print(f"- [UPDATE] Rule '{rule_id}': Adding semicolon.")
                print(f"    Old: {sql_query}")
                print(f"    New: {new_query}")
            else:
                print(f"- [OK] Rule '{rule_id}' already has a semicolon or is empty.")

        if not rules_to_update:
            print("\nAll queries appear to be correct. No updates needed.")
            return

        # Execute the updates
        print(f"\nApplying {len(rules_to_update)} updates to the database...")
        cursor.executemany("UPDATE L1_Rules SET sql_query = ? WHERE Rule_ID = ?", rules_to_update)
        conn.commit()
        print("Database updates applied successfully.")

    except sqlite3.Error as e:
        print(f"\nDatabase error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    fix_l1_rule_queries()
