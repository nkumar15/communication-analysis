
import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(BACKEND_DIR))

from modules.domains.nse.services.rag_service import RagService
from infrastructure.logging import get_logger

logger = get_logger(__name__)

async def main():
    rag = RagService()
    
    # Define PDF file path
    files_to_ingest = [
        {
            "filename": "tcs_concall_Q2_FY26.pdf",
            "report_type": "concall",
            "doc_type": "concall"
        },
        {
            "filename": "tcs_earnings_q2_fy26_results.pdf",
            "report_type": "earnings",
            "doc_type": "earnings"
        }
    ]

    # Relative path definition
    current_dir = Path(__file__).resolve().parent
    base_dir = current_dir.parent.parent / "datasets/nse/source_documents/test"

    # Use provided existing Tenant ID
    TEST_TENANT_ID = UUID("05b51fa4-45f4-50c2-b3f4-4c122000347b")
    
    for item in files_to_ingest:
        file_name = item["filename"]
        file_path = base_dir / file_name
        
        if not file_path.exists():
            logger.error(f"Error: File not found at {file_path}")
            continue
            
        # Calculate real content hash
        import hashlib
        with open(file_path, "rb") as f:
            content = f.read()
            content_hash = hashlib.sha256(content).hexdigest()
        
        metadata = {
            "company_name": "TCS",
            "report_type": item["report_type"],
            "financial_period": "Q2_FY26",
            "doc_type": item["doc_type"],
            "original_filename": file_name,
            "content_hash": content_hash 
        }
        
        logger.info(f"Ingesting {file_path}...")
        logger.info(f"Metadata: {metadata}")
        
        try:
            res = await rag.ingest_document(
                db=None, 
                tenant_id=TEST_TENANT_ID, 
                file_path=str(file_path), 
                document_metadata=metadata
            )
            logger.info(f"Ingestion Success for {file_name}: {res}")
        except Exception as e:
            logger.error(f"Ingestion Failed for {file_name}: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
