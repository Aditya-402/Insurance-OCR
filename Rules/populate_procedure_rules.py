import sqlite3
import csv
import os

# Define the paths to the database and CSV file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'rules.db')
CSV_PATH = os.path.join(BASE_DIR, 'Procedural_rules.csv')
TABLE_NAME = 'Procedure_rules'

def create_and_populate_table():
    """
    Creates the Procedure_rules table in rules.db and populates it 
    with data from Procedural_rules.csv.
    If the table already exists, it will attempt to insert data, 
    which might fail if there are primary key conflicts.
    For a clean load, ensure the table is dropped or emptied first if needed.
    """
    conn = None  # Initialize conn to None
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create the Procedure_rules table if it doesn't exist
        # Proc_ID as TEXT PRIMARY KEY, Proc_Name TEXT, Poc_Type TEXT, Check_Rules TEXT
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            Proc_ID TEXT PRIMARY KEY,
            Proc_Name TEXT,
            Poc_Type TEXT,
            Check_Rules TEXT
        );
        """
        cursor.execute(create_table_sql)
        print(f"Table '{TABLE_NAME}' created successfully or already exists.")

        # Open and read the CSV file
        with open(CSV_PATH, 'r', newline='', encoding='utf-8') as csvfile:
            csv_reader = csv.reader(csvfile)
            header = next(csv_reader)  # Skip the header row

            # Prepare the insert statement
            insert_sql = f"INSERT OR IGNORE INTO {TABLE_NAME} (Proc_ID, Proc_Name, Poc_Type, Check_Rules) VALUES (?, ?, ?, ?)"
            # Using INSERT OR IGNORE to skip rows if Proc_ID already exists

            rows_inserted = 0
            rows_skipped = 0
            for row in csv_reader:
                if len(row) == 4: # Ensure row has the expected number of columns
                    try:
                        cursor.execute(insert_sql, (row[0], row[1], row[2], row[3]))
                        if cursor.rowcount > 0:
                            rows_inserted += 1
                        else:
                            rows_skipped +=1 # Row was ignored (likely due to existing Proc_ID)
                    except sqlite3.IntegrityError as ie:
                        print(f"Skipping row due to integrity error (likely duplicate Proc_ID): {row[0]} - {ie}")
                        rows_skipped += 1
                else:
                    print(f"Skipping row due to incorrect column count: {row}")

        # Commit the changes
        conn.commit()
        print(f"Successfully inserted {rows_inserted} new records into '{TABLE_NAME}'.")
        if rows_skipped > 0:
            print(f"{rows_skipped} rows were skipped (possibly due to existing Proc_ID or other integrity constraints).")

    except sqlite3.Error as e:
        print(f"SQLite error occurred: {e}")
        if conn:
            conn.rollback() # Rollback changes if any error occurs
    except FileNotFoundError:
        print(f"Error: The file '{CSV_PATH}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        if conn:
            conn.rollback()
    finally:
        # Close the database connection
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    create_and_populate_table()
