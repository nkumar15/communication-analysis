"""
Script to extract sample communications for AI analysis testing.
"""

# Read the flattened CSV
csv_path = "/home/neeraj/codes/enterprisesso/backend/scripts/evaluation/datasets/enron/source/emails_flattened.csv"
df = pd.read_csv(csv_path)

print(f"Total communications in dataset: {len(df)}")
print("\n" + "="*80)
print("SAMPLE EMAILS FOR TESTING")
print("="*80)

# Get a few diverse samples
samples = []

# Try to get emails with different characteristics
keywords_fraud = ['LJM', 'Raptor', 'Chewco', 'SPE', 'off-balance']
keywords_evasion = ['cell', 'offline', 'delete', 'shred', 'personal email']

# Find a fraud-related email
fraud_email = None
for idx, row in df.iterrows():
    body = str(row.get('body', '')).lower()
    if any(keyword.lower() in body for keyword in keywords_fraud):
        fraud_email = row
        break

# Find an evasion-related email  
evasion_email = None
for idx, row in df.iterrows():
    body = str(row.get('body', '')).lower()
    if any(keyword.lower() in body for keyword in keywords_evasion):
        evasion_email = row
        break

# Get a normal business email (first one that's not too short)
normal_email = None
for idx, row in df.iterrows():
    body = str(row.get('body', ''))
    if len(body) > 100 and len(body) < 1000:
        normal_email = row
        break

# Print the samples
count = 1

if fraud_email is not None:
    print(f"\n{count}. SAMPLE EMAIL - POTENTIAL FRAUD")
    print("-" * 80)
    print(f"From: {fraud_email.get('from', 'N/A')}")
    print(f"To: {fraud_email.get('to', 'N/A')}")
    print(f"Subject: {fraud_email.get('subject', 'N/A')}")
    print(f"Date: {fraud_email.get('date', 'N/A')}")
    print(f"\nBody:\n{fraud_email.get('body', 'N/A')[:1000]}")
    print("\n" + "="*80)
    count += 1

if evasion_email is not None:
    print(f"\n{count}. SAMPLE EMAIL - POTENTIAL EVASION")
    print("-" * 80)
    print(f"From: {evasion_email.get('from', 'N/A')}")
    print(f"To: {evasion_email.get('to', 'N/A')}")
    print(f"Subject: {evasion_email.get('subject', 'N/A')}")
    print(f"Date: {evasion_email.get('date', 'N/A')}")
    print(f"\nBody:\n{evasion_email.get('body', 'N/A')[:1000]}")
    print("\n" + "="*80)
    count += 1

if normal_email is not None:
    print(f"\n{count}. SAMPLE EMAIL - BUSINESS AS USUAL")
    print("-" * 80)
    print(f"From: {normal_email.get('from', 'N/A')}")
    print(f"To: {normal_email.get('to', 'N/A')}")
    print(f"Subject: {normal_email.get('subject', 'N/A')}")
    print(f"Date: {normal_email.get('date', 'N/A')}")
    print(f"\nBody:\n{normal_email.get('body', 'N/A')[:1000]}")
    print("\n" + "="*80)

print("\n\nCopy any of the above email bodies to test in the UI!")
