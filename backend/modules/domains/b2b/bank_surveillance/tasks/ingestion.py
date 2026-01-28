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
import logging
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from workers.b2b_domain_worker.celery_app import celery_app

# Increase CSV field size limit
csv.field_size_limit(2**31 - 1)

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="bank_surveillance.ingest_daily_dump", queue="b2b-domain", max_retries=2)
def ingest_daily_dump(self, file_path: str, date: str, tenant_id: str = None, index_vectors: bool = False, region_code: str = "SG"):
    """
    Celery Task: Ingests a daily dump file (CSV) into the communications table.
    Runs in separate thread with fresh engine for isolation (avoids event loop conflicts).
    
    Args:
        file_path: Path to CSV file.
        date: YYYYMMDD date identifier for this dump.
        tenant_id: Optional tenant UUID string. Defaults to script-generated UUID.
        index_vectors: Whether to index content into Elasticsearch for RAG.
        region_code: Default region code to map data to (default: "SG").
    """
    # index_vectors defaults to False (Keyword only). 
    # If True, we enable Semantic Embeddings.
    
    job_id = uuid.uuid4()
    
    def _thread_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def _dedicated_task():
            # Create DEDICATED engine for this thread/loop to avoid sharing asyncpg pool
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
            from core.config import settings
            
            db_url = settings.database_url
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            
            engine = create_async_engine(db_url, pool_size=1, max_overflow=0)
            
            DedicatedSessionLocal = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            
            try:
                async with DedicatedSessionLocal() as db:
                    return await _run_ingestion_async(
                        job_id, file_path, date, tenant_id, index_vectors, region_code, db
                    )
            finally:
                await engine.dispose()
        
        try:
            return loop.run_until_complete(_dedicated_task())
        finally:
            loop.close()
    
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(_thread_runner).result()
            return result
    except Exception as exc:
        logger.error(f"Failed to ingest file {file_path}: {exc}")
        raise self.retry(exc=exc)


def run_ingestion(file_path: str, date: str, tenant_id: str = None, index_vectors: bool = False, region_code: str = "SG"):
    """
    Synchronous wrapper for CLI/script usage.
    
    Usage:
        from tasks.ingestion import run_ingestion
        run_ingestion("/data/20231027.csv", "20231027")
    """
    # index_vectors defaults to False (Keyword only)
    
    job_id = uuid.uuid4()
    return asyncio.run(_run_ingestion_async_standalone(job_id, file_path, date, tenant_id, index_vectors, region_code))


async def _run_ingestion_async_standalone(
    job_id: uuid.UUID, 
    file_path: str, 
    date: str, 
    tenant_id_str: str = None,
    index_vectors: bool = False,
    region_code: str = "SG"
) -> dict:
    """Standalone async runner for CLI usage - creates its own session."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from core.config import settings
    
    db_url = settings.database_url
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(db_url, pool_size=1, max_overflow=0)
    DedicatedSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with DedicatedSessionLocal() as db:
            return await _run_ingestion_async(job_id, file_path, date, tenant_id_str, index_vectors, region_code, db)
    finally:
        await engine.dispose()


async def _run_ingestion_async(
    job_id: uuid.UUID, 
    file_path: str, 
    date: str, 
    tenant_id_str: str = None,
    index_vectors: bool = False,
    region_code: str = "SG",
    db = None
) -> dict:
    """
    Core async implementation of the ingestion logic.
    
    - Sets RLS context for tenant
    - Inserts messages into PostgreSQL (communications table)
    - Optionally indexes content into Elasticsearch for RAG search
    """
    from email.utils import parsedate_to_datetime
    from core.db.rls import rls_service
    from modules.domains.b2b.bank_surveillance.services.ingestion import CommunicationIngestionService, EmailParsedData
    from modules.domains.b2b.bank_surveillance.services.rag import communication_rag_service
    from modules.domains.b2b.bank_surveillance.models.ingestion_log import IngestionLog
    from modules.b2b.models.geographic_region import GeographicRegion
    from sqlalchemy import select
    
    tenant_id = uuid.UUID(tenant_id_str) if tenant_id_str else uuid.uuid5(uuid.NAMESPACE_DNS, "ingest-task")
    
    # CRITICAL: Set RLS context for tenant BEFORE any inserts or lookups
    # Use tenant context to satisfy RLS policy for insert (tenant_id match) and region lookup
    await rls_service.set_tenant_context(db, tenant_id)

    # Resolve region code to UUID
    forced_region_id = None
    if region_code:
        region_res = await db.execute(select(GeographicRegion.id).where(
            GeographicRegion.code == region_code,
            GeographicRegion.tenant_id == tenant_id
        ))
        forced_region_id = region_res.scalar_one_or_none()
        if not forced_region_id and region_code == "SG":
             # Fallback: maybe specific tenant logic or just allow None if not found (though user wants force SG)
             logger.warning(f"Region code {region_code} not found for tenant {tenant_id}")
    
    # Create log entry
    log_entry = IngestionLog(
        job_id=job_id,
        date=date,
        file_path=file_path,
        status="running",
        started_at=datetime.utcnow()
    )
    db.add(log_entry)
    await db.commit()
    # Re-apply RLS context after commit (SET LOCAL is transaction-scoped)
    await rls_service.set_tenant_context(db, tenant_id)
    
    try:
        service = CommunicationIngestionService(db) 
        count = 0
        skipped = 0
        errors = 0
        events_created = 0
        indexed_in_transaction = []
        vector_batch = []
        vector_batch_size = 50

        if os.path.isfile(file_path) and file_path.endswith(".csv"):
            # CSV mode
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # ... (Parsing logic same as before) ...
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
                    result_code = await service.ingest_message_with_status(email_data, tenant_id, source_ref="csv_row", forced_region_id=forced_region_id)
                    
                    if result_code == "inserted":
                        count += 1
                        
                        # Queue for vector indexing
                        text_content = f"Subject: {email_data.subject}\n\n{email_data.body}"
                        metadata = {
                            "message_id": email_data.message_id,
                            "sender": email_data.sender[:200],
                            "recipients": ",".join(email_data.recipients)[:500],
                            "date": str(email_data.date),
                            "tenant_id": str(tenant_id)
                        }
                        vector_batch.append({
                            "text": text_content, 
                            "metadata": metadata,
                            "doc_id": email_data.message_id
                        })
                        
                        # Batch index
                        if len(vector_batch) >= vector_batch_size:
                            await communication_rag_service.index_batch(vector_batch, enable_semantic=index_vectors)
                            # Track indexed IDs for rollback
                            indexed_in_transaction.extend([d['doc_id'] for d in vector_batch])
                            vector_batch = []
                            
                    elif result_code == "skipped":
                        skipped += 1
                    else:
                        errors += 1
                    
                    # Batch commit every 100
                    if (count + skipped + errors) % 100 == 0:
                        try:
                            # 1. READ-AFTER-WRITE Requirement:
                            # We have ALREADY indexed documents into Elasticsearch (Lines 220).
                            # This ensures they are immediately searchable.
                            
                            # 2. COMMIT:
                            await db.commit()
                            
                            # 3. SUCCESS:
                            # If commit succeeds, the data is permanent in both DB and ES.
                            # We can clear our rollback tracking list.
                            indexed_in_transaction = [] 
                            
                        except Exception:
                            # 4. COMPENSATING TRANSACTION (Rollback):
                            # The DB commit failed (e.g. RLS Violation, Constraint Error).
                            # The DB transaction is automatically rolled back by Postgres.
                            # BUT, Elasticsearch does not rollback automatically.
                            # We must MANUALLY delete the "Ghost Records" we just indexed.
                            logger.error("DB Commit failed. Rolling back Elasticsearch...")
                            if indexed_in_transaction:
                                await communication_rag_service.delete_documents(indexed_in_transaction)
                            raise
                        
                        await rls_service.set_tenant_context(db, tenant_id)
                        if count > 0 and count % 100 == 0:
                            logger.info(f"  Processed {count} messages (Skipped: {skipped}, Errors: {errors})...")
            
            # Final vector batch (must index before final commit checks)
            if vector_batch:
                await communication_rag_service.index_batch(vector_batch, enable_semantic=index_vectors)
                indexed_in_transaction.extend([d['doc_id'] for d in vector_batch])

            # Final commit
            try:
                await db.commit()
                indexed_in_transaction = []
            except Exception:
                # Same Rollback Logic as above
                logger.error("Final DB Commit failed. Rolling back Elasticsearch...")
                if indexed_in_transaction:
                    await communication_rag_service.delete_documents(indexed_in_transaction)
                raise

            await rls_service.set_tenant_context(db, tenant_id)
            
            # --- DETECTION PHASE ---
            logger.info("Starting detection phase...")
            from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
            detection_service = DetectionService(db, tenant_id)
            events_created = await detection_service.analyze_unprocessed(limit=1000)
            await db.commit()
            await rls_service.set_tenant_context(db, tenant_id)
            logger.info(f"Detection complete. Created {events_created} RiskEvents")
            
        else:
            # Directory mode (uses existing bulk_ingest which handles files)
            count = await service.bulk_ingest([file_path], base_tenant_id=tenant_id)
            events_created = 0 # No detection for directory mode for now
        
        # Update log entry
        log_entry.status = "completed"
        log_entry.processed_count = count
        log_entry.error_count = errors
        log_entry.completed_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"✅ Ingestion Complete. Processed: {count}, Skipped: {skipped}, Errors: {errors}, RiskEvents: {events_created}")
        return {"job_id": str(job_id), "status": "completed", "processed": count, "skipped": skipped, "errors": errors, "risk_events": events_created}
        
    except Exception as e:
        await db.rollback()
        log_entry.status = "failed"
        log_entry.completed_at = datetime.utcnow()
        try:
            db.add(log_entry)
            await db.commit()
        except:
            pass
        logger.error(f"❌ Ingestion Failed: {e}")
        raise e
    finally:
        # Close RAG service connections
        try:
            await communication_rag_service.close()
        except:
            pass


# CLI Entry Point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest daily dump into Bank Surveillance")
    parser.add_argument("file_path", help="Path to CSV file or directory")
    parser.add_argument("--date", required=True, help="Date identifier (YYYYMMDD)")
    parser.add_argument("--tenant-id", help="Optional tenant UUID")
    parser.add_argument("--enable-vectors", action="store_true", help="Enable Semantic Embeddings (Slow/Costly)")
    
    args = parser.parse_args()
    
    run_ingestion(
        args.file_path, 
        args.date, 
        args.tenant_id, 
        index_vectors=args.enable_vectors,
        region_code="SG" 
    )
