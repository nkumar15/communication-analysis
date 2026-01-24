
import asyncio
import argparse
import sys
import os
import uuid

# Add backend to sys.path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../../.."))

from modules.domains.b2b.bank_surveillance.tasks.ingestion import run_ingestion as task_run_ingestion, _run_ingestion_async_standalone

# Fixed Tenant ID from scripts/seeds/README.md
DEMO_TENANT_ID = "b5e1fa40-89f4-50c2-a3f4-4c122000beef"

def ingest_enron_csv(file_path: str, tenant_id: str = DEMO_TENANT_ID, enable_vectors: bool = False):
    """
    Ingest a CSV file into the Bank Surveillance system (Postgres + Elasticsearch).
    Default Tenant: Worldwide Bank (Demo Tenant).
    """
    print(f"🚀 Starting Ingestion for {file_path}")
    print(f"🏢 Tenant ID: {tenant_id}")
    print(f"🔍 Semantic Search (Vectors): {'ENABLED' if enable_vectors else 'DISABLED (Keyword Only)'}")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
        
    # Extract date from filename if possible (e.g. 20011030.csv -> 20011030)
    filename = os.path.basename(file_path)
    date_str = filename.split(".")[0]
    if not date_str.isdigit() or len(date_str) != 8:
        date_str = "20000101" # Fallback
        
    try:
        # We reuse the standalone runner from the task module
        # This handles DB session creation and async loop
        job_id = uuid.uuid4()
        result = asyncio.run(_run_ingestion_async_standalone(
            job_id=job_id,
            file_path=file_path,
            date=date_str,
            tenant_id_str=tenant_id,
            index_vectors=enable_vectors
        ))
        
        print(f"\n✅ Ingestion Finished!")
        print(f"   Processed: {result.get('processed', 0)}")
        print(f"   Errors: {result.get('errors', 0)}")
        print(f"   Risk Events Created: {result.get('risk_events', 0)}")
        
    except Exception as e:
        print(f"\n❌ Ingestion Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Enron CSV for Bank Surveillance Demo")
    parser.add_argument("file_path", help="Path to the CSV file (e.g., data/dumps/20011030.csv)")
    parser.add_argument("--tenant-id", default=DEMO_TENANT_ID, help="Target Tenant ID (Defaults to Demo Tenant)")
    parser.add_argument("--enable-vectors", action="store_true", help="Enable Semantic Embeddings (Slow). Default is Keyword Only.")
    
    args = parser.parse_args()
    
    ingest_enron_csv(args.file_path, args.tenant_id, args.enable_vectors)
