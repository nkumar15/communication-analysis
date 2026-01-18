import asyncio
import os
import glob
from pathlib import Path
import sys
import uuid
# Add /app to sys.path to ensure modules can be imported
sys.path.append("/app")

from modules.domains.b2b.bank_surveillance.services.policy import policy_rag_service
from modules.domains.b2b.bank_surveillance.constants import DEFAULT_TENANT_ID

async def ingest_regulations():
    # Path to regulation text files
    # In container, this is /app/scripts/...
    reg_dir = "/app/scripts/evaluation/datasets/regulations"
    files = glob.glob(os.path.join(reg_dir, "*.txt"))
    
    print(f"📚 Found {len(files)} regulatory documents in {reg_dir}")
    
    for file_path in files:
        print(f"   Indexing: {file_path}")
        
        # Simple metadata
        metadata = {
            "filename": os.path.basename(file_path),
            "type": "regulation"
        }
        
        # We reuse the ingest_document method from BaseRagService (via PolicyRagService)
        # Note: BaseRagService usually expects database integration, but looking at `ingest_document`,
        # it might require a DB session if we strictly follow the pattern. 
        # However, for pure RAG (BaseRagService logic), we can check `rag.py` implementation.
        # Actually `BaseRagService.ingest_document` primarily calls `vector_store.add`.
        # Let's check `rag.py` or just use the llama_index mechanics directly if easier? 
        # But for consistency, let's use the service method.
        
        # UPDATE: BaseRagService.ingest_document signature:
        # async def ingest_document(self, db: AsyncSession, tenant_id: UUID, file_path: str, document_metadata: Dict[str, Any] = None)
        # It takes 'db' to potentially store document record. 
        # Since regulations don't have a SQL table in our current POC plan (just vector store), 
        # we might need to mock the db session or bypass it.
        
        # Actually, let's just do direct LlamaIndex ingestion here for simplicity as we don't have a 'regulations' SQL table yet.
        # This keeps it lightweight.
        
        # Reuse the service method (passing None for db as it's not used in this path)
        await policy_rag_service.ingest_document(
            db=None, 
            tenant_id=DEFAULT_TENANT_ID, 
            file_path=file_path, 
            document_metadata=metadata
        )
        
    print("✅ Regulations Ingestion Complete.")

if __name__ == "__main__":
    asyncio.run(ingest_regulations())
