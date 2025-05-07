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
    claim_id = os.path.splitext(os.path.basename(file_path))[0]
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r"(?P<field>.*?) :: (?P<value>.*?) :: (?P<page>.*?) \|\|"
    matches = re.finditer(pattern, content, re.MULTILINE)
    grouped_data = defaultdict(list)
    for match in matches:
        field = match.group("field").strip().replace(" ", "_").replace("?", "")
        value = match.group("value").strip()
        page = match.group("page").strip().replace(" ", "_")
        col_name = f"{page}.{field}"
        col_name = normalize_col(col_name)
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

def process_all_txt_files(db_path=None, db_folder=None):
    db_path = db_path or DB_PATH
    db_folder = db_folder or DB_FOLDER
    db_full_path = os.path.join(os.getcwd(), db_path) if not os.path.isabs(db_path) else db_path
    # Ensure the directory for the DB exists
    db_dir = os.path.dirname(db_full_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    folder = os.path.join(os.getcwd(), db_folder)
    conn = sqlite3.connect(db_full_path)
    for filename in os.listdir(folder):
        print(filename)
        if filename.endswith(TXT_EXT):
            file_path = os.path.join(folder, filename)
            print(f"Processing file: {file_path}")
            try:
                process_txt_file(file_path, conn)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
    conn.close()
    print("All eligible .txt files processed and saved to the database.")

if __name__ == "__main__":
    process_all_txt_files()
