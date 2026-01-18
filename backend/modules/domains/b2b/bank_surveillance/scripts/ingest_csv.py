import asyncio
import csv
import sys
import os
from pathlib import Path
from datetime import datetime
from email.utils import parsedate_to_datetime

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.db.session import AsyncSessionLocal
from modules.domains.b2b.bank_surveillance.constants import DEFAULT_TENANT_ID
from modules.domains.b2b.bank_surveillance.models.enron_email import EnronEmail

# Increase CSV field size limit for large bodies
csv.field_size_limit(sys.maxsize)

# Docker path: /app/scripts/...
CSV_PATH = "/app/scripts/evaluation/datasets/enron/source/emails_flattened.csv"

async def ingest_csv(csv_path: str, batch_size: int = 1000, limit: int = None):
    print(f"Ingesting from {csv_path}...")
    
    if not os.path.exists(csv_path):
        print(f"Error: File {csv_path} not found.")
        return

    async with AsyncSessionLocal() as session:
        batch = []
        count = 0
        total_ingested = 0
        
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Parse date
                    try:
                        dt = parsedate_to_datetime(row['date'])
                    except:
                        dt = datetime.now()

                    # Combine recipients
                    recipients = []
                    if row.get('recipients'): recipients.extend(row['recipients'].split(','))
                    if row.get('cc'): recipients.extend(row['cc'].split(','))
                    if row.get('bcc'): recipients.extend(row['bcc'].split(','))
                    recipients = [r.strip() for r in recipients if r.strip()]

                    email_obj = EnronEmail(
                        message_id=row['message_id'],
                        sender=row['sender'],
                        recipients=recipients,
                        subject=row['subject'],
                        body=row['body'],
                        date=dt,
                        tenant_id=DEFAULT_TENANT_ID
                    )
                    batch.append(email_obj)
                    count += 1
                    
                    if len(batch) >= batch_size:
                        session.add_all(batch)
                        await session.commit()
                        total_ingested += len(batch)
                        print(f"Ingested {total_ingested} emails...")
                        batch = []
                        
                    if limit and total_ingested >= limit:
                        break

                except Exception as e:
                    print(f"Skipping row error: {e}")
                    continue

        if batch:
            session.add_all(batch)
            await session.commit()
            total_ingested += len(batch)
            
        print(f"✅ Ingestion Complete. Total: {total_ingested}")

if __name__ == "__main__":
    # Ingest first 10,000 for POC to avoid long wait, or remove limit for full
    # For now, let's do 50,000 to get a good graph
    asyncio.run(ingest_csv(CSV_PATH, limit=50000))
