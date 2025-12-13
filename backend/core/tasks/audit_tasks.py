"""
Celery Tasks for Audit Logging

Background tasks for persisting audit logs asynchronously.
"""

from core.tasks.celery_app import celery_app
from core.database import AsyncSessionLocal
import asyncio
import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def run_async(coro):
    """
    Run an async coroutine, handling the case where we're already in an event loop.
    This is needed for Celery eager mode during tests.
    """
    try:
        loop = asyncio.get_running_loop()
        # Already in an async context - use nest_asyncio pattern
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No running loop - use asyncio.run()
        return asyncio.run(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def persist_audit_log(self, audit_data: dict):
    """
    Persist audit log entry asynchronously.
    
    Args:
        audit_data: Dictionary containing audit log fields (UUIDs as strings)
    
    Retry: Up to 3 times with 60 second delay
    """
    try:
        run_async(_persist_audit_log_async(audit_data))
    except Exception as exc:
        logger.error(f"Failed to persist audit log: {exc}")
        raise self.retry(exc=exc)


async def _persist_audit_log_async(audit_data: dict):
    """Async implementation of persist_audit_log"""
    # Create NEW database session
    async with AsyncSessionLocal() as db:
        try:
            from services.b2b.models import AuditLog
            from core.rls import rls_service
            
            # Convert string UUIDs back to UUID objects
            tenant_id = UUID(audit_data['tenant_id']) if audit_data.get('tenant_id') else None
            actor_id = UUID(audit_data['actor_id']) if audit_data.get('actor_id') else None
            resource_id = UUID(audit_data['resource_id']) if audit_data.get('resource_id') else None
            
            # Set RLS context for this session
            if tenant_id:
                await rls_service.set_tenant_context(db, str(tenant_id))
            
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
