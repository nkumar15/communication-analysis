import os
import asyncio
import uuid
from pathlib import Path

from modules.domains.b2c.finance_trader.services.rag_service import RagService
    

async def ingest_baseline():
    print("--- Ingesting Baseline Document (TCS Q2) ---")
    
    rag_service = RagService()
    
    # Neeraj's Tenant
    tenant_id = uuid.UUID("05b51fa4-45f4-50c2-b3f4-4c122000347b")
    
    # Path in container
    file_path = "/app/scripts/nse/data/raw/test/tcs_q2_fy26_results.pdf"
    
    if not os.path.exists(file_path):
        # Fallback for local testing
        file_path = str(Path(__file__).parent / "data/raw/test/tcs_q2_fy26_results.pdf")
    
    print(f"Target File: {file_path}")
    
    try:
        # We pass None for DB session as inspection showed it's unused in the current implementation
        result = await rag_service.ingest_document(
            db=None, 
            tenant_id=tenant_id, 
            file_path=file_path,
            document_metadata={"company": "TCS", "period": "Q2FY26", "type": "Results"}
        )
        print("Ingestion Result:", result)
        
    except Exception as e:
        print(f"Ingestion Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(ingest_baseline())
