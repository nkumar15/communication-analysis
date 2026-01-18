import pandas as pd
import email
from email.policy import default
import os
import sys

# Define paths
DATASET_DIR = "backend/scripts/evaluation/datasets/enron/source"
INPUT_FILE = os.path.join(DATASET_DIR, "emails.csv")
OUTPUT_FILE = os.path.join(DATASET_DIR, "emails_flattened.csv")

def parse_email(raw_message):
    try:
        msg = email.message_from_string(raw_message, policy=default)
        
        # Extract fields
        message_id = msg.get("Message-ID", "").strip()
        date = msg.get("Date", "").strip()
        sender = msg.get("From", "").strip()
        
        # Recipients
        def get_recipients(header_name):
            to_list = msg.get_all(header_name, [])
            return ", ".join([t.strip() for t in to_list if t]) if to_list else ""

        to = get_recipients("To")
        cc = get_recipients("Cc")
        bcc = get_recipients("Bcc")
        
        subject = msg.get("Subject", "").strip()
        
        # Extract Body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_content()
        else:
            body = msg.get_content()
            
        return {
            "message_id": message_id,
            "date": date,
            "sender": sender,
            "recipients": to,
            "cc": cc,
            "bcc": bcc,
            "subject": subject,
            "body": body
        }
    except Exception as e:
        return None

import csv
from dateutil import parser
from datetime import datetime, timezone

def flatten_emails():
    print(f"Reading {INPUT_FILE}...")
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found.")
        return

    # Increase CSV field size limit for large emails
    csv.field_size_limit(sys.maxsize)

    # Statistics
    stats = {
        "total_processed": 0,
        "kept": 0,
        "discarded": 0,
        "discarded_too_old": 0,  # < 1998
        "discarded_too_new": 0,  # > 2002
        "discarded_parse_error": 0
    }

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8', errors='replace') as infile, \
             open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as outfile:
            
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            
            # Write Header
            headers = ["message_id", "date", "sender", "recipients", "cc", "bcc", "subject", "body"]
            writer.writerow(headers)
            
            # Skip input header
            next(reader, None)
            
            for row in reader:
                if len(row) < 2:
                    continue
                    
                stats["total_processed"] += 1
                
                # The 'message' column is the second column (index 1)
                raw_msg = row[1]
                parsed = parse_email(raw_msg)
                
                if parsed and parsed["date"]:
                    # Date Filtering
                    try:
                        # Try parsing with dateutil
                        dt = parser.parse(parsed["date"])
                        # Ensure timezone awareness for comparison if needed, or just compare years
                        year = dt.year
                        
                        if 1998 <= year <= 2002:
                            writer.writerow([
                                parsed["message_id"],
                                parsed["date"],
                                parsed["sender"],
                                parsed["recipients"],
                                parsed["cc"],
                                parsed["bcc"],
                                parsed["subject"],
                                parsed["body"]
                            ])
                            stats["kept"] += 1
                        else:
                            stats["discarded"] += 1
                            if year < 1998:
                                stats["discarded_too_old"] += 1
                            else:
                                stats["discarded_too_new"] += 1
                    except:
                        stats["discarded"] += 1
                        stats["discarded_parse_error"] += 1
                else:
                    stats["discarded"] += 1
                    stats["discarded_parse_error"] += 1
                    
                if stats["total_processed"] % 1000 == 0:
                    print(f"Processed {stats['total_processed']} emails...")
                    
        print(f"✅ Flattened CSV saved to {OUTPUT_FILE}")
        
        # Discard Report
        print("\n" + "="*40)
        print("          DISCARD STATISTICS")
        print("="*40)
        print(f"Total Emails Processed: {stats['total_processed']:,}")
        print(f"✅ Emails Kept (1998-2002): {stats['kept']:,} ({stats['kept']/stats['total_processed']*100:.1f}%)")
        print(f"❌ Emails Discarded: {stats['discarded']:,}")
        print("-" * 30)
        print(f"   • Too Old (< 1998): {stats['discarded_too_old']:,}")
        print(f"   • Too New (> 2002): {stats['discarded_too_new']:,}")
        print(f"   • Parse/Date Errors: {stats['discarded_parse_error']:,}")
        print("="*40 + "\n")
        
    except Exception as e:
        print(f"❌ Error processing CSV: {e}")

if __name__ == "__main__":
    flatten_emails()
