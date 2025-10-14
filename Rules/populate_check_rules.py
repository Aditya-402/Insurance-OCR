import sqlite3
import csv
import os

# Define the paths to the database and CSV file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'rules.db')
CSV_PATH = os.path.join(BASE_DIR, 'rules_tbl.csv')
TABLE_NAME = 'Check_Rules'

def populate_table_from_csv():
    """
    Populates the Check_Rules table in rules.db with data from rules_tbl.csv.
    Existing data in Check_Rules will be deleted before new data is inserted.
    """
    conn = None  # Initialize conn to None
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Delete existing data from the Check_Rules table
        cursor.execute(f"DELETE FROM {TABLE_NAME};")
        print(f"Successfully deleted all existing records from '{TABLE_NAME}'.")

        # Open and read the CSV file
        with open(CSV_PATH, 'r', newline='') as csvfile:
            csv_reader = csv.reader(csvfile)
            header = next(csv_reader)  # Skip the header row

            # Prepare the insert statement
            # Assuming the CSV columns are 'Rules_ID' and 'Rules_description'
            # and the table Check_Rules has corresponding columns
            insert_sql = f"INSERT INTO {TABLE_NAME} (rule_id, rule_description) VALUES (?, ?)"

            rows_inserted = 0
            for row in csv_reader:
                if len(row) == 2: # Ensure row has the expected number of columns
                    cursor.execute(insert_sql, (row[0], row[1]))
                    rows_inserted += 1
                else:
                    print(f"Skipping row due to incorrect column count: {row}")

        # Commit the changes
        conn.commit()
        print(f"Successfully inserted {rows_inserted} new records into '{TABLE_NAME}' from '{os.path.basename(CSV_PATH)}'.")

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
    populate_table_from_csv()
