"""
Celery task for ingesting daily communication dumps (YYYYMMDD).
Triggered via API or scheduled via Celery Beat.

Supports both:
- Celery task execution: ingest_daily_dump.delay(file_path, date)
- Script execution: run_ingestion(file_path, date)
"""
import asyncio
import uuid
import os
import csv
from datetime import datetime
from typing import Optional
from core.db.session import AsyncSessionLocal
from modules.domains.b2b.bank_surveillance.services.ingestion import CommunicationIngestionService, EmailParsedData
from modules.domains.b2b.bank_surveillance.services.rag import communication_rag_service
from modules.domains.b2b.bank_surveillance.models.ingestion_log import IngestionLog
from workers.b2b_domain_worker.celery_app import celery_app

# Increase CSV field size limit
csv.field_size_limit(2**31 - 1)

@celery_app.task(bind=True, name="bank_surveillance.ingest_daily_dump", queue="b2b-domain")
def ingest_daily_dump(self, file_path: str, date: str, tenant_id: str = None, index_vectors: bool = False):
    """
    Celery Task: Ingests a daily dump file (CSV or directory) into the communications table.
    
    Args:
        file_path: Path to CSV or directory containing email files.
        date: YYYYMMDD date identifier for this dump.
        tenant_id: Optional tenant UUID string. Defaults to script-generated UUID.
        index_vectors: Whether to index content into Elasticsearch for RAG.
    """
    # FORCE DISABLE RAG/ES for now (User Request)
    index_vectors = False
    
    job_id = uuid.uuid4()
    
    # Run the async ingestion in new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            run_ingestion_async(job_id, file_path, date, tenant_id, index_vectors)
        )
        return result
    finally:
        loop.close()


def run_ingestion(file_path: str, date: str, tenant_id: str = None, index_vectors: bool = False):
    """
    Synchronous wrapper for CLI/script usage.
    
    Usage:
        from tasks.ingestion import run_ingestion
        run_ingestion("/data/20231027.csv", "20231027")
    """
    # FORCE DISABLE RAG/ES for now
    index_vectors = False
    
    job_id = uuid.uuid4()
    return asyncio.run(run_ingestion_async(job_id, file_path, date, tenant_id, index_vectors))


async def run_ingestion_async(
    job_id: uuid.UUID, 
    file_path: str, 
    date: str, 
    tenant_id_str: str = None,
    index_vectors: bool = False
) -> dict:
    """
    Core async implementation of the ingestion logic.
    
    - Inserts messages into PostgreSQL (communications table)
    - Optionally indexes content into Elasticsearch for RAG search
    """
    from email.utils import parsedate_to_datetime
    
    tenant_id = uuid.UUID(tenant_id_str) if tenant_id_str else uuid.uuid5(uuid.NAMESPACE_DNS, "ingest-task")
    
    async with AsyncSessionLocal() as session:
        # Create log entry
        log_entry = IngestionLog(
            job_id=job_id,
            date=date,
            file_path=file_path,
            status="running",
            started_at=datetime.utcnow()
        )
        session.add(log_entry)
        await session.commit()
        
        try:
            service = CommunicationIngestionService(session)
            count = 0
            errors = 0
            vector_batch = []
            vector_batch_size = 50
            
            if os.path.isfile(file_path) and file_path.endswith(".csv"):
                # CSV mode
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            dt = parsedate_to_datetime(row.get('date', ''))
                        except:
                            dt = datetime.now()
                        
                        recipients = [r.strip() for r in row.get('recipients', '').split(',') if r.strip()]
                        
                        email_data = EmailParsedData(
                            message_id=row.get('message_id', str(uuid.uuid4())),
                            sender=row.get('sender', 'unknown'),
                            recipients=recipients or ['unknown'],
                            subject=row.get('subject', ''),
                            body=row.get('body', ''),
                            date=dt
                        )
                        
                        # Insert into DB
                        success = await service.ingest_message(email_data, tenant_id, source_ref="csv_row")
                        
                        if success:
                            count += 1
                            
                            # Queue for vector indexing (SKIPPED if index_vectors=False)
                            if index_vectors:
                                text_content = f"Subject: {email_data.subject}\n\n{email_data.body}"
                                metadata = {
                                    "message_id": email_data.message_id,
                                    "sender": email_data.sender[:200],
                                    "recipients": ",".join(email_data.recipients)[:500],
                                    "date": str(email_data.date),
                                    "tenant_id": str(tenant_id)
                                }
                                vector_batch.append({"text": text_content, "metadata": metadata})
                                
                                # Batch index
                                if len(vector_batch) >= vector_batch_size:
                                    await communication_rag_service.index_batch(vector_batch)
                                    vector_batch = []
                        else:
                            errors += 1
                        
                        # Batch commit every 100
                        if count % 100 == 0:
                            await session.commit()
                            print(f"  Processed {count} messages...")
                
                # Final batch
                await session.commit()
                if vector_batch:
                    await communication_rag_service.index_batch(vector_batch)
                    
            else:
                # Directory mode (uses existing bulk_ingest which handles files)
                count = await service.bulk_ingest([file_path], base_tenant_id=tenant_id)
                # Note: Directory mode vectors are handled inside ingest_file via RAG service if source_ref is valid file
            
            # Update log entry
            log_entry.status = "completed"
            log_entry.processed_count = count
            log_entry.error_count = errors
            log_entry.completed_at = datetime.utcnow()
            await session.commit()
            
            print(f"✅ Ingestion Complete. Total: {count}, Errors: {errors}")
            return {"job_id": str(job_id), "status": "completed", "processed": count, "errors": errors}
            
        except Exception as e:
            log_entry.status = "failed"
            log_entry.completed_at = datetime.utcnow()
            await session.commit()
            print(f"❌ Ingestion Failed: {e}")
            raise e
        finally:
            # Close RAG service connections
            await communication_rag_service.close()


# CLI Entry Point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest daily dump into Bank Surveillance")
    parser.add_argument("file_path", help="Path to CSV file or directory")
    parser.add_argument("--date", required=True, help="Date identifier (YYYYMMDD)")
    parser.add_argument("--tenant-id", help="Optional tenant UUID")
    parser.add_argument("--skip-vectors", action="store_true", help="Skip Elasticsearch indexing")
    
    args = parser.parse_args()
    
    run_ingestion(
        args.file_path, 
        args.date, 
        args.tenant_id, 
        index_vectors=not args.skip_vectors
    )
