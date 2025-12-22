"""
Celery Tasks for Audit Logging

Background tasks for persisting audit logs.
Uses ThreadPoolExecutor to run async code in a separate thread.
"""

from workers.b2b_worker.celery_app import celery_app
from core.db.session import AsyncSessionLocal
import asyncio
import logging
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def persist_audit_log(self, audit_data: dict):
    """
    Persist audit log entry.
    Runs async code in separate thread to avoid event loop conflicts.
    Creates a fresh engine/session to ensure thread safety.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from core.config import settings
    
    # Run in thread with NEW event loop
    def _thread_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def _dedicated_task():
            # Create DEDICATED engine for this thread/loop to avoid sharing asyncpg pool
            # Must handle postgres:// fix similar to database.py
            db_url = settings.database_url
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
                
            # Minimal pool size
            engine = create_async_engine(db_url, pool_size=1, max_overflow=0)
            
            AsyncSessionLocal = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            
            try:
                async with AsyncSessionLocal() as db:
                    await _persist_audit_log_async(audit_data, db)
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
        logger.error(f"Failed to persist audit log: {exc}")
        raise self.retry(exc=exc)


async def _persist_audit_log_async(audit_data: dict, db):
    """Async implementation of persist_audit_log using injected session"""
    from services.b2b.models import AuditLog
    from core.db.rls import rls_service
    
    try:
        # Convert string UUIDs back to UUID objects
        tenant_id = UUID(audit_data['tenant_id']) if audit_data.get('tenant_id') else None
        actor_id = UUID(audit_data['actor_id']) if audit_data.get('actor_id') else None
        resource_id = UUID(audit_data['resource_id']) if audit_data.get('resource_id') else None
        
        # Set RLS context for this session
        if tenant_id:
            await rls_service.set_tenant_context(db, tenant_id)
        
        # Create audit log entry
        audit_log = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            event_type=audit_data.get('event_type'),
            resource_type=audit_data.get('resource_type'),
            resource_id=resource_id,
            details=audit_data.get('details', {}),
            ip_address=audit_data.get('ip_address'),
            user_agent=audit_data.get('user_agent')
        )
        
        db.add(audit_log)
        await db.commit()
        
        logger.info(f"✅ Audit log persisted: {audit_data.get('event_type')}")
        
    except Exception as e:
        logger.error(f"❌ Failed to persist audit log: {e}")
        await db.rollback()
        raise
