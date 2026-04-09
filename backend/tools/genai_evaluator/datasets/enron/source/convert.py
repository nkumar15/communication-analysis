import csv
import os
import sys
import email.utils
from collections import defaultdict
from datetime import datetime

# Increase CSV field size limit to handle large email bodies
csv.field_size_limit(sys.maxsize)

INPUT_FILE = "emails_flattened.csv"
OUTPUT_DIR = "../../../../data/dumps"  # Relative to this script: backend/tools/genai_evaluator/datasets/enron/source/

def parse_date(date_str):
    try:
        # RFC 2822 format: "Mon, 14 May 2001 16:39:00 -0700"
        dt = email.utils.parsedate_to_datetime(date_str)
        return dt.strftime('%Y%m%d')
    except Exception:
        return None

def convert():
    # Ensure output directory exists (using absolute path based on known structure if possible, or relative)
    # The script is in backend/tools/genai_evaluator/datasets/enron/source/
    # We want valid dumps in enterprisesso/data/dumps (mapped to /data in container)
    # Based on the user's previous request context, the goal is to make these available to the ingestion API.
    # The ingestion API looks in /data/dumps inside the container.
    # The docker-compose mounts ./data:/data.
    # So we need to write to enterprisesso/data/dumps.
    
    # Path resolution
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Walk up to 'enterprisesso' root
    root_dir = os.path.abspath(os.path.join(script_dir, "../../../../../../"))
    output_dir = os.path.join(root_dir, "data", "dumps")
    
    input_path = os.path.join(script_dir, INPUT_FILE)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    print(f"Reading from: {input_path}")
    print(f"Writing to:   {output_dir}")

    # Buffer to hold rows for each date to minimize file I/O operations
    buffer = defaultdict(list)
    BATCH_SIZE = 10000
    rows_processed = 0
    
    # Fieldnames from header
    fieldnames = ['message_id', 'date', 'sender', 'recipients', 'cc', 'bcc', 'subject', 'body']

    with open(input_path, 'r', encoding='utf-8', errors='replace') as infile:
        reader = csv.DictReader(infile)
        
        # Verify header
        # if reader.fieldnames != fieldnames:
        #    print(f"Warning: Expected fieldnames {fieldnames}, got {reader.fieldnames}")
        
        for row in reader:
            date_str = row.get('date')
            if not date_str:
                continue
                
            yyyymmdd = parse_date(date_str)
            if not yyyymmdd:
                continue
            
            # Map column names if needed or clean data
            # The ingestion API expects: message_id, date, sender, recipients, cc, bcc, subject, content
            # The input has 'body', we should probably rename to 'content' or keep as is if ingestion handles mapping.
            # Looking at ingestion.py, it uses pandas to read CSV. 
            # Looking at previous context or code for `ingest_daily_dump`, let's assume it maps or expects specific cols.
            # To be safe, let's keep original columns.
            
            buffer[yyyymmdd].append(row)
            rows_processed += 1

            if rows_processed % BATCH_SIZE == 0:
                print(f"Processed {rows_processed} rows...", end='\r')
                flush_buffer(buffer, output_dir, fieldnames)
                buffer.clear()

        # Final flush
        if buffer:
            flush_buffer(buffer, output_dir, fieldnames)
    
    print(f"\nDone! Processed {rows_processed} rows.")

def flush_buffer(buffer, output_dir, fieldnames):
    for date_key, rows in buffer.items():
        file_path = os.path.join(output_dir, f"{date_key}.csv")
        file_exists = os.path.exists(file_path)
        
        with open(file_path, 'a', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows)

if __name__ == "__main__":
    convert()
