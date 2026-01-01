
from workers.domain_worker.celery_app import celery_app
import asyncio
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from core.constants import DocumentStatus
from infrastructure.logging import get_logger
from modules.domains.nse.services.rag_service import RagService

logger = get_logger(__name__)

# Initialize RagService (Lazy load happens on first access inside methods if needed)
# However, importing the class is fine.
# Global import is fine, but instance shouldn't be global if it holds loop state
# from modules.domains.nse.services.rag_service import RagService 

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="domain.ingest_document", time_limit=1800, soft_time_limit=1740)
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
    # Import locally to avoid module-level side effects if any, though not strictly necessary
    
    # Run in thread with NEW event loop
    def _thread_runner():
        import asyncio
        import nest_asyncio
        
        # Apply nest_asyncio to allow re-entrant loops (LlamaIndex often needs this)
        nest_asyncio.apply()
        
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
                # Instantiate RagService HERE so it attaches to the CURRENT loop
                from modules.domains.nse.services.rag_service import RagService
                rag_service = RagService()
                
                async with AsyncSessionLocal() as db:
                    await _ingest_async(payload, db, rag_service)
            finally:
                if 'rag_service' in locals():
                    await rag_service.close()
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

async def _ingest_async(payload: Dict[str, Any], db, rag_service):
    """
    Async ingestion logic using IngestionService.
    
    This function handles RLS context setup, then delegates to IngestionService.
    """
    from modules.domains.nse.services.ingestion_service import ingestion_service
    from core.db.rls import rls_service
    
    tenant_id_str = payload.get('tenant_id')
    file_path = payload.get('file_path')
    job_id = payload.get('job_id')
    content_hash = payload.get('content_hash', '')
    metadata = payload.get('document_metadata', {})
    
    if not tenant_id_str or not file_path:
        logger.error("missing_required_payload", has_tenant=bool(tenant_id_str), has_file_path=bool(file_path))
        return

    tenant_id = UUID(tenant_id_str)
    
    # Set RLS Context (required for all DB operations)
    await rls_service.set_tenant_context(db, tenant_id)
    
    # Delegate to IngestionService
    try:
        result = await ingestion_service.process_ingestion(
            db=db,
            tenant_id=tenant_id,
            file_path=file_path,
            job_id=job_id,
            document_metadata=metadata,
            content_hash=content_hash,
            rag_service=rag_service
        )
        
        logger.info("worker_ingestion_complete", job_id=job_id, result_status=result.get('status'))
        
    except Exception as e:
        logger.error("worker_ingestion_failed", job_id=job_id, error=str(e), exc_info=True)
        raise
