import asyncio
import os
import sys
from uuid import uuid4

# Add backend to path
sys.path.append(os.getcwd())

# Set Mock LLM for validation to avoid API Key requirement
os.environ["LLM_PROVIDER"] = "mock"

from modules.domains.nse.services.rag_service import rag_service

async def main():
    print("=== Starting RAG Ingestion Validation ===")
    
    # 1. Create Dummy Document
    file_path = "sample_earnings.txt"
    content = """
    Reliance Industries Limited
    Integrated Annual Report 2023-24
    
    Financial Highlights:
    Revenue from Operations: ₹ 9,00,000 Crore
    EBITDA: ₹ 1,50,000 Crore
    Net Profit: ₹ 70,000 Crore
    
    Management Discussion and Analysis:
    The global economy showed resilience...
    Our digital services business, Jio, crossed 450 million subscribers.
    Retail business expanded physical footprint by 50%.
    
    Energy Transition:
    We are committed to Net Carbon Zero by 2035.
    New Energy Giga Factories are coming up fast in Jamnagar.
    """
    
    with open(file_path, "w") as f:
        f.write(content)
        
    print(f"Created sample file: {file_path}")
    
    # 2. Run Ingestion
    tenant_id = uuid4()
    print(f"Simulating Tenant ID: {tenant_id}")
    
    try:
        # Mock DB session (None for now as we don't use it yet in the stub)
        result = await rag_service.ingest_document(
            db=None,
            tenant_id=tenant_id,
            file_path=file_path,
            document_metadata={"company": "Reliance", "year": "2024", "type": "Annual Report"}
        )
        
        print("\n=== Ingestion Result ===")
        print(result)
        
        if result["status"] == "success":
            print("\nSUCCESS: Pipeline ran end-to-end!")
        else:
            print("\nFAILURE: Status not success")
            
    except Exception as e:
        print(f"\nERROR: Pipeline failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            print("Cleaned up sample file.")

if __name__ == "__main__":
    asyncio.run(main())
