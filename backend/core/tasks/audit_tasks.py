"""
Celery Tasks for Audit Logging

Background tasks for persisting audit logs asynchronously.
"""

from core.tasks.celery_app import celery_app
from core.database import AsyncSessionLocal
import asyncio
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def persist_audit_log(self, audit_data: dict):
    """
    Persist audit log entry asynchronously.
    
    Args:
        audit_data: Dictionary containing audit log fields
    
    Retry: Up to 3 times with 60 second delay
    """
    try:
        asyncio.run(_persist_audit_log_async(audit_data))
    except Exception as exc:
        logger.error(f"Failed to persist audit log: {exc}")
        raise self.retry(exc=exc)


async def _persist_audit_log_async(audit_data: dict):
    """Async implementation of persist_audit_log"""
    # Create NEW database session
    async with AsyncSessionLocal() as db:
        try:
            from services.b2b.models import AuditLog
            
            # Create audit log entry
            audit_log = AuditLog(**audit_data)
            db.add(audit_log)
            await db.commit()
            
            logger.info(f"✅ Audit log persisted: {audit_data.get('event_type')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to persist audit log: {e}")
            await db.rollback()
            raise
