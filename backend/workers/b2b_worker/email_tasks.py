"""
Celery Tasks for Email Sending

Background tasks for sending invitation emails using Celery.
Each task creates its own database session to avoid lock issues.
"""

import os
from workers.b2b_worker.celery_app import celery_app
from core.db.session import AsyncSessionLocal
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import asyncio
import logging
from typing import List
from uuid import UUID
from datetime import datetime

logger = logging.getLogger(__name__)

# Check for test mode
IS_TESTING = os.environ.get('TESTING', '').lower() in ('true', '1', 'yes')


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_invitation_email(self, invitation_id: str, tenant_id: str):
    """
    Send individual invitation email.
    Runs in separate thread with fresh engine for isolation.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from core.config import settings
    
    # Run in thread with NEW event loop
    def _thread_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def _dedicated_task():
            # Create DEDICATED engine for this thread/loop to avoid sharing asyncpg pool
            db_url = settings.database_url
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
                
            engine = create_async_engine(db_url, pool_size=1, max_overflow=0)
            
            AsyncSessionLocal = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            
            try:
                # Use injected session
                async with AsyncSessionLocal() as db:
                    await _send_invitation_email_async(invitation_id, tenant_id, db)
            finally:
                await engine.dispose()
                
        try:
            loop.run_until_complete(_dedicated_task())
        finally:
            loop.close()

    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_thread_runner).result()
    except Exception as exc:
        logger.error(f"Failed to send invitation email {invitation_id}: {exc}")
        raise self.retry(exc=exc)


async def _send_invitation_email_async(invitation_id: str, tenant_id: str, db):
    """Async implementation of send_invitation_email using injected session"""
    try:
        from services.b2b.models import InvitationModel
        from infrastructure.email import email_service
        
        # Fetch invitation with tenant data
        result = await db.execute(
            select(InvitationModel)
            .options(selectinload(InvitationModel.tenant))
            .where(InvitationModel.id == invitation_id)
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            logger.warning(f"Invitation {invitation_id} not found")
            return
        
        # In test mode, we might want to skip actual sending if not mocked?
        # But User asked for verification. We rely on mocks or allow it if safe.
        # Assuming email_service handles dev/test mode or we mock it in tests.
        
        # Send email via Resend
        await email_service.send_invitation_email(
            to_email=invitation.email,
            invitation_token=invitation.invitation_token,
            tenant_name=invitation.tenant.name,
            expires_at=invitation.expires_at
        )
        
        logger.info(f"✅ Invitation email sent to {invitation.email}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send invitation email: {e}")
        await db.rollback()
        raise


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def send_bulk_invitation_emails(self, invitation_ids: List[str], tenant_id: str):
    """
    Send multiple invitation emails in bulk.
    Runs in separate thread with fresh engine.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from core.config import settings
    from concurrent.futures import ThreadPoolExecutor
    
    # Check for test mode only to avoid sending actual emails if mocking isn't set up
    # But ideally we rely on email_service mock.
    
    def _thread_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def _dedicated_task():
            db_url = settings.database_url
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
                
            engine = create_async_engine(db_url, pool_size=1, max_overflow=0)
            AsyncSessionLocal = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            
            try:
                async with AsyncSessionLocal() as db:
                    await _send_bulk_invitation_emails_async(invitation_ids, tenant_id, db)
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
        logger.error(f"Failed to send bulk invitation emails: {exc}")
        raise self.retry(exc=exc)


async def _send_bulk_invitation_emails_async(invitation_ids: List[str], tenant_id: str, db):
    """Async implementation of send_bulk_invitation_emails using injected session"""
    try:
        from services.b2b.models import InvitationModel
        from infrastructure.email import email_service
        
        # Fetch all invitations
        result = await db.execute(
            select(InvitationModel)
            .options(selectinload(InvitationModel.tenant))
            .where(InvitationModel.id.in_(invitation_ids))
        )
        invitations = result.scalars().all()
        
        success_count = 0
        failure_count = 0
        
        # Send emails (continue even if some fail)
        for invitation in invitations:
            try:
                await email_service.send_invitation_email(
                    to_email=invitation.email,
                    invitation_token=invitation.invitation_token,
                    tenant_name=invitation.tenant.name,
                    expires_at=invitation.expires_at
                )
                
                success_count += 1
                logger.info(f"✅ Sent email to {invitation.email}")
                
            except Exception as e:
                failure_count += 1
                logger.error(f"❌ Failed to send to {invitation.email}: {e}")
                # Continue with next email
        
        logger.info(
            f"📧 Bulk emails completed: {success_count} success, "
            f"{failure_count} failures (of {len(invitation_ids)} total)"
        )
        
    except Exception as e:
        logger.error(f"❌ Bulk email task failed: {e}")
        await db.rollback()
        raise
