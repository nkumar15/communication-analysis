import os
import sys
import asyncio
import argparse
import uuid
import csv
from pathlib import Path
from email.utils import parsedate_to_datetime
from datetime import datetime

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.append(str(PROJECT_ROOT))
if os.path.exists("/app") and "/app" not in sys.path:
    sys.path.append("/app")

from core.db.session import AsyncSessionLocal
from modules.domains.b2b.bank_surveillance.services.ingestion import CommunicationIngestionService, EmailParsedData

# Increase CSV field size limit
csv.field_size_limit(sys.maxsize)

async def ingest_csv(file_path: str, service: CommunicationIngestionService, base_tenant_id: uuid.UUID, batch_size: int = 100):
    print(f"Ingesting CSV: {file_path}")
    
    count = 0
    batch_count = 0
    
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
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
                recipients = [r.strip() for r in recipients if r.strip()]

                email_data = EmailParsedData(
                    message_id=row['message_id'],
                    sender=row['sender'],
                    recipients=recipients,
                    subject=row['subject'],
                    body=row['body'],
                    date=dt
                )
                
                success = await service.ingest_message(email_data, base_tenant_id, source_ref="csv_row")
                if success:
                    count += 1
                    batch_count += 1
                
                if batch_count >= batch_size:
                    await service.db.commit()
                    batch_count = 0
                    print(f"Committed {count} messages...")
                    
            except Exception as e:
                print(f"Error processing CSV row: {e}")
                continue

    if batch_count > 0:
        await service.db.commit()
        
    print(f"CSV Ingestion complete. Total: {count}")


async def ingest_directory(directory: str, batch_size: int = 100):
    # Check if input is actually a file (CSV)
    if os.path.isfile(directory) and directory.endswith(".csv"):
        async with AsyncSessionLocal() as session:
            service = CommunicationIngestionService(session)
            # Default tenant for ingestion
            base_tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, "ingest-script")
            await ingest_csv(directory, service, base_tenant_id, batch_size)
        return

    print(f"Scanning directory: {directory}")
    
    file_paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
             # Skip hidden files
            if file.startswith("."):
                continue
            file_paths.append(os.path.join(root, file))
            
    print(f"Found {len(file_paths)} files.")
    
    if not file_paths:
        return

    async with AsyncSessionLocal() as session:
        service = CommunicationIngestionService(session)
        print("Starting ingestion (Communication)...")
        
        # Default tenant for ingestion script
        base_tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, "ingest-script")
        
        total_ingested = 0
        chunk_size = 500
        
        for i in range(0, len(file_paths), chunk_size):
            chunk = file_paths[i : i + chunk_size]
            count = await service.bulk_ingest(chunk, base_tenant_id=base_tenant_id, batch_size=batch_size)
            total_ingested += count
            print(f"Processed {min(i + chunk_size, len(file_paths))}/{len(file_paths)} files. (Ingested: {total_ingested})")

    print(f"Ingestion complete. Total messages ingested: {total_ingested}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest dataset (Directory or CSV) into Bank Surveillance")
    parser.add_argument("path", help="Path to the dataset root directory OR csv file")
    parser.add_argument("--batch-size", type=int, default=100, help="DB batch commit size")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"Error: Directory {args.directory} not found.")
        sys.exit(1)
        
    asyncio.run(ingest_directory(args.directory, args.batch_size))
