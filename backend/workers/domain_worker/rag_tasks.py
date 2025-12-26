
from workers.domain_worker.celery_app import celery_app
import asyncio
import logging
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from modules.domains.nse.services.rag_service import RagService

logger = logging.getLogger(__name__)

# Initialize RagService (Lazy load happens on first access inside methods if needed)
# However, importing the class is fine.
rag_service = RagService()

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="domain.ingest_document")
def ingest_document_task(self, payload: Dict[str, Any]):
    """
    Async Ingestion Task using ThreadPoolExecutor pattern.
    Payload:
    - tenant_id (str)
    - file_path (str)
    - document_metadata (dict)
    - job_id (str) - For status updates
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from core.config import settings
    
    # Run in thread with NEW event loop
    def _thread_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def _dedicated_task():
            # Create DEDICATED engine
            from sqlalchemy.engine import make_url
            
            db_url = settings.database_url
            url_obj = make_url(db_url)
            
            # Switch driver to asyncpg
            if url_obj.drivername == "postgresql":
                url_obj = url_obj.set(drivername="postgresql+asyncpg")
            
            # Asyncpg doesn't support 'sslmode' in query params, it expects 'ssl' context in connect_args
            # For 'disable', we just remove it.
            # For 'require', we would need to pass ssl context.
            # Since env is setup for disable, we just strip it.
            query = dict(url_obj.query)
            if "sslmode" in query:
                del query["sslmode"]
            url_obj = url_obj.set(query=query)
            
            engine = create_async_engine(url_obj, pool_size=1, max_overflow=0)
            AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            
            try:
                async with AsyncSessionLocal() as db:
                    await _ingest_async(payload, db)
            finally:
                await engine.dispose()
                
        try:
            loop.run_until_complete(_dedicated_task())
        finally:
            loop.close()

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_thread_runner).result()
    except Exception as exc:
        logger.error(f"Failed to ingest document: {exc}")
        # Could update status to FAILED here if not already done in _ingest_async
        # But retrying might be better first.
        raise self.retry(exc=exc)

async def _ingest_async(payload: Dict[str, Any], db):
    from modules.b2b.models.rag_document import RagDocument
    from core.db.rls import rls_service
    from sqlalchemy import select
    
    tenant_id_str = payload.get('tenant_id')
    file_path = payload.get('file_path')
    job_id = payload.get('job_id')
    metadata = payload.get('document_metadata', {})
    
    if not tenant_id_str or not file_path:
        logger.error("Missing tenant_id or file_path")
        return

    tenant_id = UUID(tenant_id_str)
    
    # Set RLS Context
    await rls_service.set_tenant_context(db, tenant_id)
    
    # Update Status to PROCESSING
    # We update the RagDocument record which should already exist (created by API)
    # API should generate 'job_id' and save it to DB, or we query by job_id.
    
    rag_doc = None
    if job_id:
        # Find document by job_id
        # Note: job_id is unique enough? Or filter by tenant validation.
        stmt = select(RagDocument).where(RagDocument.job_id == job_id)
        result = await db.execute(stmt)
        rag_doc = result.scalars().first()
        
        if rag_doc:
            rag_doc.status = "processing"
            await db.commit()
            # CRITICAL: RLS context (SET LOCAL) is lost after commit. Re-apply it for subsequent updates.
            await rls_service.set_tenant_context(db, tenant_id)
            logger.info(f"Updated RagDocument {rag_doc.id} status to PROCESSING")
        else:
             logger.warning(f"RagDocument for job_id {job_id} not found. Proceeding with ingestion anyway.")

    try:
        # Call Service
        result = await rag_service.ingest_document(
            db=db,
            tenant_id=tenant_id,
            file_path=file_path,
            document_metadata=metadata
        )
        
        # Update Status to COMPLETED
        if rag_doc:
            rag_doc.status = "completed" # or 'ready'
            rag_doc.chunk_count = result.get('chunks', 0)
            rag_doc.error_message = None
            await db.commit()
            logger.info(f"Ingestion successful for {file_path}")

    except Exception as e:
        logger.error(f"Ingestion logic failed: {e}")
        if rag_doc:
            rag_doc.status = "failed"
            rag_doc.error_message = str(e)
            await db.commit()
        raise
