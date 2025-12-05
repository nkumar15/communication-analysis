from uuid import UUID
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from core.database import AsyncSessionLocal
from services.b2b.models.audit_log import AuditLog
import logging

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
        self,
        tenant_id: UUID,
        event_type: str,
        resource_type: str,
        actor_id: Optional[UUID] = None,
        resource_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log an audit event to the database.
        Designed to be run as a BackgroundTask.
        """
        try:
            # Extract IP and User Agent from request if provided
            if request:
                client_ip = request.client.host if request.client else None
                # Handle X-Forwarded-For if behind proxy (like our nginx)
                forwarded = request.headers.get("X-Forwarded-For")
                if forwarded:
                    client_ip = forwarded.split(",")[0]
                
                ip_address = ip_address or client_ip
                user_agent = user_agent or request.headers.get("User-Agent")

            audit_log = AuditLog(
                tenant_id=tenant_id,
                actor_id=actor_id,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Since this method might be called directly or via background task,
            # let's use a context manager for a fresh session to be safe and independent.
            # CRITICAL: We MUST set the RLS context for the fresh session
            async with AsyncSessionLocal() as session:
                from sqlalchemy import text
                await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
                session.add(audit_log)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to write audit log: {str(e)}")
            # We don't raise here to prevent crashing the main application flow

async def log_audit_background(
    tenant_id: UUID,
    event_type: str,
    resource_type: str,
    actor_id: Optional[UUID] = None,
    resource_id: Optional[UUID] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """
    Standalone function to be used with BackgroundTasks.
    Creates its own AuditService instance and database session.
    """
async def log_audit_background(
    tenant_id: UUID,
    event_type: str,
    resource_type: str,
    actor_id: Optional[UUID] = None,
    resource_id: Optional[UUID] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """
    Standalone function to be used with BackgroundTasks.
    Creates its own AuditService instance and database session.
    """
    try:
        # We don't need to pass db session here as AuditService creates a fresh one
        service = AuditService(db=None) 
        await service.log_event(
            tenant_id=tenant_id,
            event_type=event_type,
            resource_type=resource_type,
            actor_id=actor_id,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        logger.error(f"Failed to write audit log: {str(e)}")
