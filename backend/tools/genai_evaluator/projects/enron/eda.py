import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# Define paths
DATASET_DIR = "backend/scripts/evaluation/datasets/enron/source"
RESULTS_DIR = "backend/scripts/evaluation/results/enron"
CSV_FILE = os.path.join(DATASET_DIR, "emails_flattened.csv") # Updated input
REPORT_FILE = os.path.join(RESULTS_DIR, "enron_eda_report.md")

def generate_eda_report():
    print(f"Starting EDA on {CSV_FILE}...")
    
    if not os.path.exists(CSV_FILE):
        print(f"❌ Error: {CSV_FILE} not found. Please run flatten_emails.py first.")
        return

    # Load Data
    try:
        df = pd.read_csv(CSV_FILE)
        print(f"✅ Loaded {len(df)} emails.")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    # Basic Stats
    total_emails = len(df)
    unique_senders = df['sender'].nunique()
    
    # Date Processing
    # 1. Count empty strings first (matches user's "Missing" view)
    empty_dates = df['date'].isna().sum() + (df['date'].astype(str).str.strip() == '').sum()
    
    # 2. Parse robustly with explicit format first
    def parse_date(x):
        if pd.isna(x) or str(x).strip() == '':
            return pd.NaT
        
        # Try explicit format: Wed, 31 Oct 2001 22:04:18 -0800
        # Format: %a, %d %b %Y %H:%M:%S %z
        try:
            return pd.to_datetime(x, format="%a, %d %b %Y %H:%M:%S %z", utc=True)
        except:
            pass
            
        # Try dateutil as fallback
        try:
            return pd.to_datetime(parser.parse(x), utc=True)
        except:
            return pd.NaT

    df['parsed_date'] = df['date'].apply(parse_date)
    
    # Analyze failures
    failed_rows = df[df['parsed_date'].isna() & df['date'].notna() & (df['date'].astype(str).str.strip() != '')]
    if not failed_rows.empty:
        print(f"\n⚠️  WARNING: {len(failed_rows)} dates failed to parse. Sample:")
        print(failed_rows['date'].unique()[:10])
        print("--------------------------------------------------\n")
    
    # Log suspicious dates for user debugging
    future_dates = df[df['parsed_date'].dt.year > 2005]
    if not future_dates.empty:
        print("\n⚠️  WARNING: Found dates > 2005:")
        print(future_dates[['date', 'parsed_date']].head(10).to_string())
        print("--------------------------------------------------\n")

    # Calculate invalid date count for reporting (dates > 2003)
    # We define "valid" as 1990-2003 for the purpose of this specific metric
    invalid_dates_mask = (df['parsed_date'].dt.year > 2003) | (df['parsed_date'].dt.year < 1990)
    invalid_date_count = df['parsed_date'][invalid_dates_mask].count()

    # Time range
    min_date = df['parsed_date'].min()
    max_date = df['parsed_date'].max()
    
    print(f"Date Range found: {min_date} to {max_date}")
    print(f"Invalid Dates Count: {invalid_date_count}")
    
    return
    # Sender Distribution
    top_senders = df['sender'].value_counts().head(10)

    # Recipient Analysis (To, Cc, Bcc)
    df['cc_count'] = df['cc'].fillna('').apply(lambda x: len(x.split(',')) if x else 0)
    df['bcc_count'] = df['bcc'].fillna('').apply(lambda x: len(x.split(',')) if x else 0)
    
    avg_cc = df['cc_count'].mean()
    avg_bcc = df['bcc_count'].mean()

    # Generate Markdown Report
    with open(REPORT_FILE, "w") as f:
        f.write("# Enron Dataset EDA Report\n\n")
        f.write(f"**Date:** {pd.Timestamp.now()}\n")
        f.write(f"**Source:** `{CSV_FILE}`\n\n")
        
        f.write("## 1. General Statistics\n")
        f.write(f"- **Total Emails:** {total_emails:,}\n")
        f.write(f"- **Unique Senders:** {unique_senders:,}\n")
        f.write(f"- **Valid Time Range (1990-2003):** {min_date} to {max_date}\n\n")
        
        f.write("## 2. Communication Stats\n")
        f.write(f"- **Avg. Cc recipients per email:** {avg_cc:.2f}\n")
        f.write(f"- **Avg. Bcc recipients per email:** {avg_bcc:.2f}\n")
        f.write(f"- **Emails with Bcc:** {len(df[df['bcc_count'] > 0]):,}\n\n")

        f.write("## 3. Top 10 Senders\n")
        f.write("| Sender | Count |\n")
        f.write("|---|---|\n")
        for sender, count in top_senders.items():
            f.write(f"| {sender} | {count:,} |\n")
        f.write("\n")
        
        f.write("## 4. Data Integrity\n")
        f.write(f"- **Missing Date Headers (Empty):** {empty_dates} ({empty_dates/total_emails*100:.1f}%)\n")
        f.write(f"- **Failed Date Parse:** {df['parsed_date'].isna().sum() - empty_dates}\n")
        f.write(f"- **Out of Range Dates (>2003):** {invalid_date_count}\n")
        f.write(f"- **Missing Senders:** {df['sender'].isna().sum()}\n")
        f.write(f"- **Empty Bodies:** {df['body'].isna().sum()}\n")

    print(f"✅ EDA Report generated at {REPORT_FILE}")

if __name__ == "__main__":
    generate_eda_report()
