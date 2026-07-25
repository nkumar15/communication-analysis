"""
Celery task for Workflow B: Group + Alert.

Aggregates RiskEvents into Incidents and generates Alerts.
Triggered via API from the UI.
"""
import asyncio
import uuid
import logging
from datetime import date, datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from workers.b2b_domain_worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="bank_surveillance.generate_alerts", queue="b2b-domain", max_retries=2)
def generate_alerts(
    self, 
    tenant_id: str, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None
):
    """
    Celery Task: Aggregates RiskEvents into Incidents and generates Alerts.
    
    Args:
        tenant_id: Tenant UUID string
        start_date: Optional YYYY-MM-DD filter
        end_date: Optional YYYY-MM-DD filter
    """
    def _thread_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def _dedicated_task():
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
                    return await _run_aggregation_async(
                        db, tenant_id, start_date, end_date
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
        logger.error(f"Failed to generate alerts: {exc}")
        raise self.retry(exc=exc)


async def _run_aggregation_async(
    db,
    tenant_id_str: str,
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None
) -> dict:
    """Core async implementation of aggregation logic."""
    from core.db.rls import rls_service
    from modules.domains.b2b.bank_surveillance.services.aggregation import AggregationService
    
    tenant_id = uuid.UUID(tenant_id_str)
    
    # Set RLS context
    await rls_service.set_platform_admin_context(db)
    
    # Parse dates
    start_date = None
    end_date = None
    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    # Run aggregation
    service = AggregationService(db, tenant_id)
    result = await service.run_full_aggregation(start_date, end_date)
    
    await db.commit()
    
    logger.info(
        f"✅ Aggregation Complete. Events: {result['events_processed']}, "
        f"Incidents: {result['incidents_created']}, Alerts: {result['alerts_created']}"
    )
    
    return {
        "status": "completed",
        "events_processed": result["events_processed"],
        "incidents_created": result["incidents_created"],
        "alerts_created": result["alerts_created"],
    }


def run_aggregation_sync(tenant_id: str, start_date: str = None, end_date: str = None) -> dict:
    """Synchronous wrapper for CLI/script usage."""
    return asyncio.run(_run_aggregation_standalone(tenant_id, start_date, end_date))


async def _run_aggregation_standalone(
    tenant_id_str: str,
    start_date_str: str = None,
    end_date_str: str = None
) -> dict:
    """Standalone async runner for CLI."""
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
            return await _run_aggregation_async(db, tenant_id_str, start_date_str, end_date_str)
    finally:
        await engine.dispose()
