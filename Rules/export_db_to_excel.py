import sqlite3
import pandas as pd
import os
from datetime import datetime

def export_db_to_excel():
    """
    Exports all tables from rules.db to an Excel file with each table as a separate sheet.
    """
    # Define the path to the database
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'rules.db')
    
    # Create timestamp for the output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_FILE = os.path.join(BASE_DIR, f'rules_export_{timestamp}.xlsx')
    
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        
        # Get all table names
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in the database.")
            return
        
        # Create a Pandas Excel writer using XlsxWriter as the engine
        with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
            for table in tables:
                table_name = table[0]
                
                # Read the table into a DataFrame
                print(f"Exporting table: {table_name}")
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                
                # Write the DataFrame to an Excel sheet
                df.to_excel(writer, sheet_name=table_name, index=False)
                
                # Get the xlsxwriter workbook and worksheet objects
                workbook = writer.book
                worksheet = writer.sheets[table_name]
                
                # Add some formatting to make the headers stand out
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })
                
                # Apply the header format to the header row
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Set column widths
                for i, col in enumerate(df.columns):
                    # Set column width based on max length in the column
                    max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
                    worksheet.set_column(i, i, min(max_len, 30))  # Cap at 30 for readability
        
        print(f"Export completed successfully. File saved as: {OUTPUT_FILE}")
    
    except sqlite3.Error as e:
        print(f"SQLite error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    export_db_to_excel()
