import psycopg2
import os
import pandas as pd
import logging
import re
import json
from collections import defaultdict
from .config import CLAIMS_DB_CONFIG, TXT_EXT

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def normalize_col(col):
    return re.sub(r'[^a-zA-Z0-9_.]', '', col.lower().replace(' ', '_'))

def _aggregate_grouped_data(grouped_data):
    record = {}
    for key, values in grouped_data.items():
        first_valid_value = next((v for v in values if v is not None), None)
        record[key] = first_valid_value
    return record

def _write_df_to_table(conn, df, table_name, claim_id):
    if df.empty:
        return

    cols = '", "'.join(df.columns)
    placeholders = ', '.join(['%s'] * len(df.columns))
    update_cols = ', '.join([f'"{col}" = EXCLUDED."{col}"' for col in df.columns if col != 'ClaimID'])

    query = f'''
        INSERT INTO "{table_name}" ("{cols}")
        VALUES ({placeholders})
        ON CONFLICT ("ClaimID") DO UPDATE SET {update_cols};
    '''
    
    cursor = conn.cursor()
    for _, row in df.iterrows():
        try:
            cursor.execute(query, tuple(row))
        except psycopg2.Error as e:
            logging.error(f"Error inserting/updating row for ClaimID {claim_id} in {table_name}: {e}")
            conn.rollback()
            break
    else:
        conn.commit()

def process_txt_file(file_path, conn):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return

    parts = content.split(':::')
    if len(parts) < 2:
        logging.warning(f"Skipping file {file_path}: Does not contain ':::' separator.")
        return

    claim_id = parts[0].strip()
    data_content = parts[1].strip()

    if not claim_id:
        logging.warning(f"Skipping entry in {file_path}: ClaimID is missing.")
        return

    normalized_claim_id = normalize_col(claim_id)

    excel_path = os.path.join(PROJECT_ROOT, 'Rules', 'rules.xlsx')
    try:
        df_l1_rules = pd.read_excel(excel_path, sheet_name='L1_Rules')
    except FileNotFoundError:
        logging.error(f"Schema file not found: {excel_path}")
        return

    patient_grouped_data = defaultdict(list)
    non_patient_grouped_data = defaultdict(list)
    all_fields = set(df_l1_rules['description'])

    parsed_data = json.loads(data_content)

    for item in parsed_data:
        page_category = item.get("page_category", "unknown_page")
        current_data_category = item.get("data_category", "unknown_data_category")
        
        for field in item.get("fields", []):
            original_field = field.get("field_name")
            value = field.get("value")

            if original_field in all_fields:
                normalized_field = original_field.replace(" ", "_").replace("?", "")
                normalized_page_category = page_category.replace(" ", "_")
                
                col_name = f"{normalized_page_category}.{normalized_field}"
                col_name = normalize_col(col_name)

                target_dict = patient_grouped_data if current_data_category == "patient" else non_patient_grouped_data
                target_dict[col_name].append(None if value.lower() == "not in scope" else value)

    patient_record = _aggregate_grouped_data(patient_grouped_data)
    if patient_record:
        patient_record_final = {normalize_col("ClaimID"): normalized_claim_id, **{normalize_col(k): v for k, v in patient_record.items()}}
        df_patient = pd.DataFrame([patient_record_final])
        _write_df_to_table(conn, df_patient, "PatientData", normalized_claim_id)

    non_patient_record = _aggregate_grouped_data(non_patient_grouped_data)
    if non_patient_record:
        non_patient_record_final = {normalize_col("ClaimID"): normalized_claim_id, **{normalize_col(k): v for k, v in non_patient_record.items()}}
        df_non_patient = pd.DataFrame([non_patient_record_final])
        _write_df_to_table(conn, df_non_patient, "NonPatientData", normalized_claim_id)
    logging.info(f"Data for ClaimID='{claim_id}' processed and saved to PatientData and NonPatientData tables.")

def process_all_txt_files(folder, single_file_path=None):
    conn = None
    try:
        conn = psycopg2.connect(**CLAIMS_DB_CONFIG)
        if single_file_path:
            if os.path.exists(single_file_path) and single_file_path.endswith(TXT_EXT):
                print(f"Processing single file: {single_file_path}")
                process_txt_file(single_file_path, conn)
                print(f"File {single_file_path} processed and saved to the database.")
            else:
                print(f"Error: Specified file {single_file_path} does not exist or is not a .txt file.")
        else:
            if not os.path.isdir(folder):
                print(f"Error: Folder '{folder}' does not exist or is not a directory.")
                return

            print(f"Processing all .txt files in folder: {folder}")
            processed_count = 0
            for filename in os.listdir(folder):
                if filename.endswith(TXT_EXT):
                    file_path = os.path.join(folder, filename)
                    print(f"Processing file: {file_path}")
                    process_txt_file(file_path, conn)
                    processed_count += 1
            print(f"{processed_count} eligible .txt files processed and saved to the database.")
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process text files and load data into PostgreSQL DB.")
    parser.add_argument("file_path", type=str, nargs='?', default=None,
                        help="Optional path to a single .txt file to process.")
    parser.add_argument("--folder", type=str, default='processed_output',
                        help="Folder containing .txt files to process if no specific file_path is given.")

    args = parser.parse_args()

    process_all_txt_files(folder=args.folder, single_file_path=args.file_path)
