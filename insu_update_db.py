import re
import json
import os
import sqlite3
import pandas as pd
from collections import defaultdict

DB_PATH = "claim_database.db"
DB_FOLDER = "db"
TXT_EXT = ".txt"

def normalize_col(col):
    return col.strip().replace(" ", "_").replace("?", "").lower()

def process_txt_file(file_path, conn):
    base_name_no_ext = os.path.splitext(os.path.basename(file_path))[0]
    if base_name_no_ext.endswith("_output"):
        claim_id = base_name_no_ext[:-7]  # Remove last 7 characters ("_output")
    else:
        claim_id = base_name_no_ext
    grouped_data = defaultdict(list)
    current_section_prefix = ""
    # Regex for a data line, anchored to the start of the line
    data_line_pattern = re.compile(r"^(?P<field>.*?) :: (?P<value>.*?) :: (?P<page>.*?) \|\|")

    with open(file_path, "r", encoding="utf-8") as f:
        for line_number, line_content in enumerate(f):
            line_stripped = line_content.strip()

            # Check for section headers to set the prefix
            if line_stripped == "--Patient Data--":
                current_section_prefix = "Patient_"
                continue
            elif line_stripped == "--Not Patient Data--":
                current_section_prefix = "Not_Patient_"
                continue
            elif line_stripped.startswith("--") and line_stripped.endswith("--"):
                # Any other header (e.g., --Claim Form Page 1 Data--, --Extracted Insurance/Identity Data--)
                # resets the prefix, as we only want to prefix for LLM's Patient/Not_Patient sections.
                current_section_prefix = ""
                continue
            # Page breaks also should not carry forward a prefix from a data section
            elif line_stripped.startswith("--- Page") and line_stripped.endswith("---"):
                current_section_prefix = "" # Reset prefix if it was set from a data section
                continue

            match = data_line_pattern.match(line_stripped) # Use match for line-by-line
            if match:
                original_field = match.group("field").strip()
                value = match.group("value").strip()
                page_category = match.group("page").strip() # This is the category part

                # Apply prefix if current_section_prefix is set
                field_to_use = current_section_prefix + original_field if current_section_prefix else original_field
                
                # Normalize field and page_category parts for the column name
                normalized_field = field_to_use.replace(" ", "_").replace("?", "")
                normalized_page_category = page_category.replace(" ", "_")

                col_name = f"{normalized_page_category}.{normalized_field}"
                col_name = normalize_col(col_name) # Final normalization for the full column name
                
                grouped_data[col_name].append(None if value.lower() == "not in scope" else value)
    record = {}
    for key, values in grouped_data.items():
        non_null_values = [v for v in values if v is not None]
        if len(non_null_values) > 1:
            record[key] = json.dumps(values)
        else:
            record[key] = values[0] if values else None
    record = {normalize_col("ClaimID"): claim_id, **{normalize_col(k): v for k, v in record.items()}}
    df = pd.DataFrame([record])
    df.columns = [normalize_col(col) for col in df.columns]

    # --- Dynamic schema update: add new columns if needed ---
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='ClaimsData';
    """)
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(ClaimsData);")
        existing_cols = set([normalize_col(row[1]) for row in cursor.fetchall()])
        new_cols = set(df.columns) - existing_cols
        for col in new_cols:
            alter_sql = f'ALTER TABLE ClaimsData ADD COLUMN "{col}" TEXT'
            cursor.execute(alter_sql)
        conn.commit()
    # ------------------------------------------------------

    df.to_sql("ClaimsData", conn, if_exists="append", index=False)
    print(f"✅ Data saved to table 'ClaimsData' with smart array flattening and ClaimID='{claim_id}'.")

import argparse

def process_all_txt_files(db_path=None, db_folder=None, single_file_path=None):
    db_path = db_path or DB_PATH
    db_folder = db_folder or DB_FOLDER
    db_full_path = os.path.join(os.getcwd(), db_path) if not os.path.isabs(db_path) else db_path
    # Ensure the directory for the DB exists
    db_dir = os.path.dirname(db_full_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_full_path)

    if single_file_path:
        if os.path.exists(single_file_path) and single_file_path.endswith(TXT_EXT):
            print(f"Processing single file: {single_file_path}")
            try:
                process_txt_file(single_file_path, conn)
            except Exception as e:
                print(f"Error processing {single_file_path}: {e}")
            print(f"File {single_file_path} processed and saved to the database.")
        else:
            print(f"Error: Specified file {single_file_path} does not exist or is not a .txt file.")
    else:
        folder = os.path.join(os.getcwd(), db_folder)
        if not os.path.isdir(folder):
            print(f"Error: DB_FOLDER '{folder}' does not exist or is not a directory.")
            conn.close()
            return

        print(f"Processing all .txt files in folder: {folder}")
        processed_count = 0
        for filename in os.listdir(folder):
            if filename.endswith(TXT_EXT):
                file_path = os.path.join(folder, filename)
                print(f"Processing file: {file_path}")
                try:
                    process_txt_file(file_path, conn)
                    processed_count += 1
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
        print(f"{processed_count} eligible .txt files processed and saved to the database.")

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process text files and load data into SQLite DB.")
    parser.add_argument("file_path", type=str, nargs='?', default=None,
                        help="Optional path to a single .txt file to process.")
    parser.add_argument("--db_path", type=str, default=DB_PATH,
                        help=f"Path to the SQLite database file (default: {DB_PATH}).")
    parser.add_argument("--db_folder", type=str, default=DB_FOLDER,
                        help=f"Folder containing .txt files to process if no specific file_path is given (default: {DB_FOLDER}).")

    args = parser.parse_args()

    process_all_txt_files(db_path=args.db_path, db_folder=args.db_folder, single_file_path=args.file_path)
