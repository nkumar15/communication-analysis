
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../")))

from modules.domains.b2b.bank_surveillance.services.rag import communication_rag_service

async def main():
    print("🧹 Clearing Bank Surveillance Elasticsearch Index...")
    
    rag_service = communication_rag_service
    rag_service._ensure_initialized()
    
    index_name = rag_service.get_index_name()
    
    if rag_service._vector_store_provider == "elasticsearch":
        client = rag_service.vector_store.client
        if await client.indices.exists(index=index_name):
            await client.indices.delete(index=index_name)
            print(f"✅ Deleted index: {index_name}")
        else:
            print(f"ℹ️ Index '{index_name}' does not exist.")
    else:
        print("⚠️ Not using Elasticsearch provider. Skipping.")

if __name__ == "__main__":
    asyncio.run(main())
