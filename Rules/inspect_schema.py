import sqlite3
import os

# Define the paths to the database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'rules.db')
TABLE_NAME = 'Check_Rules'

def get_table_schema():
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        print(f"Schema for table '{TABLE_NAME}':")
        cursor.execute(f"PRAGMA table_info({TABLE_NAME});")
        columns = cursor.fetchall()
        if columns:
            for col in columns:
                print(f"  Column ID: {col[0]}, Name: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, DefaultValue: {col[4]}, PK: {col[5]}")
        else:
            print(f"Table '{TABLE_NAME}' not found or has no columns.")
    except sqlite3.Error as e:
        print(f"SQLite error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    get_table_schema()
