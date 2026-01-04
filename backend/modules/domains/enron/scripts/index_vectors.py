import asyncio
import csv
import sys
import os
from pathlib import Path
from typing import List

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Adjust path for container mapping if needed, or assume standard
# In container, PROJECT_ROOT is /app
# CSV is at /app/scripts/evaluation/datasets/enron/source/emails_flattened.csv

from modules.domains.enron.services.rag import enron_rag_service
from modules.domains.enron.constants import DEFAULT_TENANT_ID
from llama_index.core import Document, VectorStoreIndex, StorageContext

CSV_PATH = "/app/scripts/evaluation/datasets/enron/source/emails_flattened.csv"

async def index_vectors(limit: int = 10000):
    print(f"🚀 Starting Vector Indexing from {CSV_PATH}...")
    
    if not os.path.exists(CSV_PATH):
        print(f"❌ Error: File {CSV_PATH} not found.")
        return

    # 1. Initialize RAG Service (Settings, Embed Model, Vector Store)
    enron_rag_service._ensure_initialized()
    print("✅ RAG Service Initialized (Connected to Elasticsearch)")

    # Increase CSV field size limit
    csv.field_size_limit(sys.maxsize)

    batch_size = 50
    documents_batch = []
    total_indexed = 0
    
    # 2. Read CSV and Create Documents
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
                
            # Create LlamaIndex Document
            # We embed the Subject + Body
            text_content = f"Subject: {row['subject']}\n\n{row['body']}"
            
            # Limit metadata size to avoid "Metadata length is longer than chunk size" error
            sender = row['sender'][:200]
            recipients = row['recipients'][:500] + "..." if len(row['recipients']) > 500 else row['recipients']
            
            doc = Document(
                text=text_content,
                metadata={
                    "message_id": row['message_id'],
                    "sender": sender,
                    "recipients": recipients,
                    "date": row['date'],
                    "tenant_id": str(DEFAULT_TENANT_ID)
                }
            )
            
            documents_batch.append(doc)
            
            # Batch Indexing
            if len(documents_batch) >= batch_size:
                await _index_batch(documents_batch)
                total_indexed += len(documents_batch)
                print(f"   Indexed {total_indexed} documents...")
                documents_batch = []
    
    # Final batch
    if documents_batch:
        await _index_batch(documents_batch)
        total_indexed += len(documents_batch)

    print(f"✅ Vector Indexing Complete. Total: {total_indexed}")

async def _index_batch(documents: List[Document]):
    # create index from documents - this automatically chunks and embeds
    # We reuse the storage context from the service
    storage_context = StorageContext.from_defaults(vector_store=enron_rag_service.vector_store)
    
    # VectorStoreIndex.from_documents handles the pipeline
    VectorStoreIndex.from_documents(
        documents, 
        storage_context=storage_context,
        show_progress=True
    )

if __name__ == "__main__":
    # Indexing can be slow (embedding generation). 
    # Start with a subset if testing, or full if ready.
    # 5000 is good for Golden Set evaluation covering common topics.
    asyncio.run(index_vectors(limit=10000))
