import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.db.session import AsyncSessionLocal
from modules.domains.b2b.bank_surveillance.services.ingestion import EnronIngestionService

async def ingest_directory(directory: str, batch_size: int = 100):
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
        service = EnronIngestionService(session)
        print("Starting ingestion...")
        
        # Batching logic is handled inside service, but we pass full list.
        # Ideally for huge datasets we'd pass an iterator or chunk the list here.
        # detailed chunking for better progress reporting:
        
        total_ingested = 0
        chunk_size = 500
        
        for i in range(0, len(file_paths), chunk_size):
            chunk = file_paths[i : i + chunk_size]
            count = await service.bulk_ingest(chunk, batch_size=batch_size)
            total_ingested += count
            print(f"Processed {min(i + chunk_size, len(file_paths))}/{len(file_paths)} files. (Ingested: {total_ingested})")

    print(f"Ingestion complete. Total emails ingested: {total_ingested}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Enron dataset into database")
    parser.add_argument("directory", help="Path to the Enron dataset root directory")
    parser.add_argument("--batch-size", type=int, default=100, help="DB batch commit size")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"Error: Directory {args.directory} not found.")
        sys.exit(1)
        
    asyncio.run(ingest_directory(args.directory, args.batch_size))
