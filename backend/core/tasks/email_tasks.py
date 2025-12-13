"""
Celery Tasks for Email Sending

Background tasks for sending invitation emails using Celery.
Each task creates its own database session to avoid lock issues.
"""

from core.tasks.celery_app import celery_app
from core.database import AsyncSessionLocal
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import asyncio
import logging
from typing import List
from uuid import UUID
from datetime import datetime

logger = logging.getLogger(__name__)


def run_async(coro):
    """
    Run an async coroutine, handling the case where we're already in an event loop.
    This is needed for Celery eager mode during tests.
    """
    try:
        loop = asyncio.get_running_loop()
        # Already in an async context - use nest_asyncio pattern or create task
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No running loop - use asyncio.run()
        return asyncio.run(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_invitation_email(self, invitation_id: str, tenant_id: str):
    """
    Send individual invitation email.
    
    Args:
        invitation_id: UUID of the invitation
        tenant_id: UUID of the tenant
    
    Retry: Up to 3 times with 60 second delay
    """
    try:
        run_async(_send_invitation_email_async(invitation_id, tenant_id))
    except Exception as exc:
        logger.error(f"Failed to send invitation email {invitation_id}: {exc}")
        raise self.retry(exc=exc)


async def _send_invitation_email_async(invitation_id: str, tenant_id: str):
    """Async implementation of send_invitation_email"""
    # Create NEW database session (avoid lock issues)
    async with AsyncSessionLocal() as db:
        try:
            from services.b2b.models import InvitationModel
            from core.email import email_service
            
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
            
            # Send email via Resend
            await email_service.send_invitation_email(
                to_email=invitation.email,
                invitation_token=invitation.invitation_token,
                tenant_name=invitation.tenant.name,
                expires_at=invitation.expires_at
            )
            
            # Update email sent timestamp
            invitation.email_sent_at = datetime.utcnow()
            await db.commit()
            
            logger.info(f"✅ Invitation email sent to {invitation.email}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send invitation email: {e}")
            await db.rollback()
            raise


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def send_bulk_invitation_emails(self, invitation_ids: List[str], tenant_id: str):
    """
    Send multiple invitation emails in bulk.
    
    Args:
        invitation_ids: List of invitation UUIDs
        tenant_id: UUID of the tenant
    
    Retry: Up to 2 times with 120 second delay
    """
    try:
        run_async(_send_bulk_invitation_emails_async(invitation_ids, tenant_id))
    except Exception as exc:
        logger.error(f"Failed to send bulk invitation emails: {exc}")
        raise self.retry(exc=exc)


async def _send_bulk_invitation_emails_async(invitation_ids: List[str], tenant_id: str):
    """Async implementation of send_bulk_invitation_emails"""
    # Create NEW database session
    async with AsyncSessionLocal() as db:
        try:
            from services.b2b.models import InvitationModel
            from core.email import email_service
            
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
                    
                    invitation.email_sent_at = datetime.utcnow()
                    success_count += 1
                    logger.info(f"✅ Sent email to {invitation.email}")
                    
                except Exception as e:
                    failure_count += 1
                    logger.error(f"❌ Failed to send to {invitation.email}: {e}")
                    # Continue with next email
            
            # Commit all updates
            await db.commit()
            
            logger.info(
                f"📧 Bulk emails completed: {success_count} success, "
                f"{failure_count} failures (of {len(invitation_ids)} total)"
            )
            
        except Exception as e:
            logger.error(f"❌ Bulk email task failed: {e}")
            await db.rollback()
            raise
