#!/usr/bin/env python3
"""
rename_pdfs.py

Usage:
    python rename_pdfs.py /path/to/input_folder /path/to/output_folder

This script will:
 - Find all .pdf files in the input folder (non-recursive).
 - Generate unique 6-digit codes (100000–999999)—one per file.
 - Copy each PDF into the output folder as <code>.pdf.
 - Create mapping.csv in output folder: original_filename,new_filename.
"""

import os
import sys
import csv
import random
import shutil
from pathlib import Path

def generate_codes(n):
    """
    Generate n unique 6-digit codes in the range [100000, 999999].
    """
    if n > 900000:
        raise ValueError("Too many files: only 900,000 unique 6-digit codes available.")
    # sample without replacement:
    return random.sample(range(100000, 1000000), n)

def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    input_folder = Path(sys.argv[1])
    output_folder = Path(sys.argv[2])
    output_folder.mkdir(parents=True, exist_ok=True)

    # Find PDF files
    pdf_files = [f for f in input_folder.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
    if not pdf_files:
        print(f"No PDF files found in {input_folder}")
        sys.exit(0)

    # Generate codes
    codes = generate_codes(len(pdf_files))

    # Prepare CSV writer
    mapping_csv = output_folder / 'mapping.csv'
    with mapping_csv.open('w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['original_filename', 'new_filename'])

        # Process each file
        for original, code in zip(pdf_files, codes):
            new_name = f"{code}.pdf"
            dest = output_folder / new_name

            # Copy the file (change to shutil.move(...) if you want to move instead)
            shutil.copy2(original, dest)

            # Write mapping
            writer.writerow([original.name, new_name])

    print(f"Renamed {len(pdf_files)} files. Mapping written to {mapping_csv}")

if __name__ == '__main__':
    main()
