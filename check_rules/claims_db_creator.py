import re
import json
import os
import sqlite3
import pandas as pd
from collections import defaultdict
import logging
from .config import DB_PATH # DATABASES_DIR is used in config, not directly here.

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Determine the project root directory (one level up from this script's location)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TXT_EXT = ".txt"

def normalize_col(col):
    return col.strip().replace(" ", "_").replace("?", "").lower()

# Helper function to write DataFrame to a specific table with dynamic schema updates
def _write_df_to_table(conn, df, table_name, claim_id):
    if df.empty:
                return

    df.columns = [normalize_col(col) for col in df.columns] # Normalize all columns before any DB operation
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
    table_exists = cursor.fetchone()

    if table_exists:
        # First, delete any existing rows for this ClaimID to prevent duplicates.
        # This effectively makes the operation an "upsert" (update/insert).
        try:
            delete_sql = f'DELETE FROM "{table_name}" WHERE {normalize_col("ClaimID")} = ?'
            cursor.execute(delete_sql, (claim_id,))
        except sqlite3.OperationalError as e:
            # This might happen if the ClaimID column doesn't exist yet, which is fine on first run.
            pass

        # Now, handle dynamic schema updates for new columns
        cursor.execute(f"PRAGMA table_info('{table_name}');")
        existing_cols_tuples = cursor.fetchall()
        existing_cols = set([normalize_col(row[1]) for row in existing_cols_tuples])
        
        new_cols = set(df.columns) - existing_cols
        
        for col in new_cols:
            try:
                alter_sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" TEXT'
                cursor.execute(alter_sql)
            except sqlite3.OperationalError as e:
                print(f"Warning: Could not add column '{col}' to table '{table_name}': {e}")
        conn.commit()

    try:
        df.to_sql(table_name, conn, if_exists="append", index=False)
        print(f"Data for ClaimID='{claim_id}' saved/appended to table '{table_name}'.")
    except Exception as e:
        print(f"Error saving data to table '{table_name}' for ClaimID='{claim_id}': {e}")

def _aggregate_grouped_data(grouped_data):
    record = {}
    if not grouped_data:
        return record
    for key, values in grouped_data.items():
        non_null_values = [v for v in values if v is not None]
        record[key] = json.dumps(values) if len(non_null_values) > 1 else (non_null_values[0] if non_null_values else None)
    return record

def process_txt_file(file_path, conn):
    claim_id = os.path.splitext(os.path.basename(file_path))[0]
    if claim_id.endswith("_output"):
        claim_id = claim_id[:-len("_output")]
    normalized_claim_id = normalize_col(claim_id)

    patient_grouped_data = defaultdict(list)
    non_patient_grouped_data = defaultdict(list)
    current_data_category = "patient"

    data_line_pattern = re.compile(r"^(?P<field>[^:]+?) :: (?P<value>.*?) :: (?P<page>.*?) \|\|")

    with open(file_path, "r", encoding="utf-8") as f:
        for line_number, line_content in enumerate(f):
            line_stripped = line_content.strip()

            if line_stripped == "--Patient Data--":
                current_data_category = "patient"
                continue
            elif line_stripped == "--Not Patient Data--":
                current_data_category = "non_patient"
                continue
            elif line_stripped.startswith("--") and line_stripped.endswith("--"):
                continue
            elif line_stripped.startswith("--- Page") and line_stripped.endswith("---"):
                continue

            match = data_line_pattern.match(line_stripped)
            if match:
                original_field = match.group("field").strip()
                value = match.group("value").strip()
                page_category = match.group("page").strip()

                normalized_field = original_field.replace(" ", "_").replace("?", "")
                normalized_page_category = page_category.replace(" ", "_")
                
                col_name = f"{normalized_page_category}.{normalized_field}"
                col_name = normalize_col(col_name)

                target_dict = patient_grouped_data if current_data_category == "patient" else non_patient_grouped_data
                target_dict[col_name].append(None if value.lower() == "not in scope" else value)

        # Process and write patient data
    patient_record = _aggregate_grouped_data(patient_grouped_data)
    if patient_record:
        patient_record_final = {normalize_col("ClaimID"): normalized_claim_id, **{normalize_col(k): v for k, v in patient_record.items()}}
        df_patient = pd.DataFrame([patient_record_final])
        _write_df_to_table(conn, df_patient, "PatientData", normalized_claim_id)

    # Process and write non-patient data
    non_patient_record = _aggregate_grouped_data(non_patient_grouped_data)
    if non_patient_record:
        non_patient_record_final = {normalize_col("ClaimID"): normalized_claim_id, **{normalize_col(k): v for k, v in non_patient_record.items()}}
        df_non_patient = pd.DataFrame([non_patient_record_final])
        _write_df_to_table(conn, df_non_patient, "NonPatientData", normalized_claim_id)
    print(f"Data for ClaimID='{claim_id}' processed and saved to PatientData and NonPatientData tables.")

import argparse

def process_all_txt_files(db_path=None, db_folder=None, single_file_path=None):
    db_path = db_path or DB_PATH
    db_folder = db_folder or DB_FOLDER
    db_full_path = db_path
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
        folder = db_folder
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
