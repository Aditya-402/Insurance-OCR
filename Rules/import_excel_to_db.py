import sqlite3
import pandas as pd
import os
import sys
from datetime import datetime

def import_excel_to_db(excel_path=None, db_path=None):
    """
    Imports all sheets from an Excel file into a SQLite database.
    Each sheet becomes a table in the database.
    
    Args:
        excel_path (str): Path to the Excel file. If None, user will be prompted.
        db_path (str): Path to the SQLite database. If None, a new one will be created.
    """
    # Define the base directory
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Handle excel_path parameter
    if not excel_path:
        excel_path = input("Enter the path to the Excel file: ")
    
    if not os.path.exists(excel_path):
        print(f"Error: File '{excel_path}' does not exist.")
        return
    
    # Handle db_path parameter
    if not db_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_path = os.path.join(BASE_DIR, f'imported_rules_{timestamp}.db')
        print(f"Creating new database at: {db_path}")
    
    conn = None
    try:
        # Connect to the database (creates it if it doesn't exist)
        conn = sqlite3.connect(db_path)
        
        # Read all sheets from the Excel file
        xl = pd.ExcelFile(excel_path)
        sheet_names = xl.sheet_names
        
        if not sheet_names:
            print("No sheets found in the Excel file.")
            return
        
        print(f"Found {len(sheet_names)} sheets in the Excel file.")
        
        # Process each sheet
        for sheet_name in sheet_names:
            print(f"Importing sheet: {sheet_name}")
            
            # Read the sheet into a DataFrame
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            
            if df.empty:
                print(f"  Sheet '{sheet_name}' is empty. Skipping.")
                continue
            
            # Clean column names (remove spaces, special chars)
            df.columns = [col.strip().replace(' ', '_') for col in df.columns]
            
            # Create the table and import the data
            df.to_sql(sheet_name, conn, if_exists='replace', index=False)
            
            # Get the number of rows imported
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {sheet_name}")
            row_count = cursor.fetchone()[0]
            print(f"  Imported {row_count} rows into table '{sheet_name}'")
        
        print(f"Import completed successfully. Database saved as: {db_path}")
    
    except sqlite3.Error as e:
        print(f"SQLite error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

def main():
    """
    Main function to handle command line arguments.
    """
    excel_path = None
    db_path = None
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
    
    if len(sys.argv) > 2:
        db_path = sys.argv[2]
    
    import_excel_to_db(excel_path, db_path)

if __name__ == '__main__':
    main()
