"""
B2C Worker Tasks

Background tasks for B2C subscription and billing operations.
"""
from celery import Task
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from workers.b2c_worker.celery_app import app
from core.database import SessionLocal
from core.utils.email import send_email
from core.config import settings
from services.b2c.models.user import B2CUser
from services.b2c.models.subscription import Subscription
from services.b2c.models.workspace import Workspace

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management."""
    _db = None
    
    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


# ============================================================================
# Subscription Email Tasks
# ============================================================================

@app.task(base=DatabaseTask, bind=True, max_retries=3)
def send_payment_failure_email(self, user_id: str, workspace_id: str, grace_period_days: int = 7):
    """
    Send email notification when payment fails.
    
    Args:
        user_id: User ID
        workspace_id: Workspace ID
        grace_period_days: Number of days in grace period
    """
    try:
        user = self.db.query(B2CUser).filter(B2CUser.id == user_id).first()
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        
        if not user or not workspace:
            logger.error(f"User or workspace not found: {user_id}, {workspace_id}")
            return
        
        subscription = self.db.query(Subscription).filter(
            Subscription.workspace_id == workspace_id
        ).first()
        
        # Send email
        send_email(
            to_email=user.email,
            subject="Payment Failed - Action Required",
            template="b2c/payment_failed",
            context={
                "user_name": user.display_name or user.email,
                "workspace_name": workspace.name,
                "tier": subscription.tier if subscription else "unknown",
                "grace_period_days": grace_period_days,
                "update_payment_url": f"{settings.frontend_url}/billing",
                "support_email": "support@example.com"
            }
        )
        
        logger.info(f"Payment failure email sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Error sending payment failure email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@app.task(base=DatabaseTask, bind=True, max_retries=3)
def send_subscription_canceled_email(self, user_id: str, workspace_id: str, reason: str = "user_request"):
    """
    Send email when subscription is canceled.
    
    Args:
        user_id: User ID
        workspace_id: Workspace ID
        reason: Cancellation reason ('user_request', 'payment_failed', 'admin')
    """
    try:
        user = self.db.query(B2CUser).filter(B2CUser.id == user_id).first()
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        
        if not user or not workspace:
            return
        
        subscription = self.db.query(Subscription).filter(
            Subscription.workspace_id == workspace_id
        ).first()
        
        send_email(
            to_email=user.email,
            subject="Subscription Canceled",
            template="b2c/subscription_canceled",
            context={
                "user_name": user.display_name or user.email,
                "workspace_name": workspace.name,
                "tier": subscription.tier if subscription else "free",
                "reason": reason,
                "period_end": subscription.current_period_end.isoformat() if subscription and subscription.current_period_end else None,
                "reactivate_url": f"{settings.frontend_url}/pricing"
            }
        )
        
        logger.info(f"Subscription canceled email sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Error sending cancellation email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@app.task(base=DatabaseTask, bind=True, max_retries=3)
def send_subscription_activated_email(self, user_id: str, workspace_id: str):
    """
    Send welcome email when subscription is activated.
    
    Args:
        user_id: User ID
        workspace_id: Workspace ID
    """
    try:
        user = self.db.query(B2CUser).filter(B2CUser.id == user_id).first()
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        
        if not user or not workspace:
            return
        
        subscription = self.db.query(Subscription).filter(
            Subscription.workspace_id == workspace_id
        ).first()
        
        send_email(
            to_email=user.email,
            subject=f"Welcome to {subscription.tier.capitalize()}!",
            template="b2c/subscription_activated",
            context={
                "user_name": user.display_name or user.email,
                "workspace_name": workspace.name,
                "tier": subscription.tier,
                "billing_interval": subscription.billing_interval,
                "amount": f"${subscription.amount_cents / 100:.2f}",
                "currency": subscription.currency,
                "dashboard_url": f"{settings.frontend_url}/dashboard",
                "billing_url": f"{settings.frontend_url}/billing"
            }
        )
        
        logger.info(f"Subscription activated email sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Error sending activation email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@app.task(base=DatabaseTask, bind=True, max_retries=3)
def send_invoice_payment_succeeded_email(self, user_id: str, invoice_id: str):
    """
    Send receipt email when invoice is paid.
    
    Args:
        user_id: User ID
        invoice_id: Invoice ID
    """
    try:
        from services.b2c.models.subscription import Invoice
        
        user = self.db.query(B2CUser).filter(B2CUser.id == user_id).first()
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        
        if not user or not invoice:
            return
        
        send_email(
            to_email=user.email,
            subject="Payment Receipt",
            template="b2c/invoice_paid",
            context={
                "user_name": user.display_name or user.email,
                "amount": f"${invoice.amount_paid / 100:.2f}",
                "currency": invoice.currency,
                "invoice_date": invoice.invoice_date.strftime("%B %d, %Y") if invoice.invoice_date else None,
                "invoice_pdf_url": invoice.invoice_pdf_url,
                "billing_url": f"{settings.frontend_url}/billing"
            }
        )
        
        logger.info(f"Invoice receipt sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Error sending invoice email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@app.task(base=DatabaseTask, bind=True, max_retries=3)
def send_grace_period_expiring_email(self, user_id: str, workspace_id: str, days_remaining: int):
    """
    Send reminder email when grace period is expiring.
    
    Args:
        user_id: User ID
        workspace_id: Workspace ID
        days_remaining: Days remaining in grace period
    """
    try:
        user = self.db.query(B2CUser).filter(B2CUser.id == user_id).first()
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        
        if not user or not workspace:
            return
        
        send_email(
            to_email=user.email,
            subject=f"Payment Required - {days_remaining} Days Remaining",
            template="b2c/grace_period_expiring",
            context={
                "user_name": user.display_name or user.email,
                "workspace_name": workspace.name,
                "days_remaining": days_remaining,
                "update_payment_url": f"{settings.frontend_url}/billing",
                "support_email": "support@example.com"
            }
        )
        
        logger.info(f"Grace period reminder sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Error sending grace period email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


# ============================================================================
# Workspace Invitation Email Tasks
# ============================================================================

@app.task(base=DatabaseTask, bind=True, max_retries=3)
def send_workspace_invitation_email(
    self, 
    invitation_id: str, 
    invitation_token: str,
    workspace_name: str,
    inviter_name: str,
    invitee_email: str,
    role: str
):
    """
    Send workspace invitation email with acceptance link.
    
    Args:
        invitation_id: Invitation ID
        invitation_token: Unique invitation token
        workspace_name: Name of workspace
        inviter_name: Name of person who invited
        invitee_email: Email of invitee
        role: Role being offered (member, admin, viewer)
    """
    try:
        # Build invitation URL
        invitation_url = f"{settings.frontend_url}/invite/{invitation_token}"
        
        send_email(
            to_email=invitee_email,
            subject=f"You've been invited to join {workspace_name}",
            template="b2c/workspace_invitation",
            context={
                "workspace_name": workspace_name,
                "inviter_name": inviter_name,
                "role": role,
                "invitation_url": invitation_url,
                "expires_days": 7,
                "support_email": "support@example.com"
            }
        )
        
        logger.info(f"Workspace invitation email sent to {invitee_email} for workspace {workspace_name}")
        
    except Exception as e:
        logger.error(f"Error sending workspace invitation email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


# ============================================================================
# Subscription Management Tasks
# ============================================================================

@app.task(base=DatabaseTask, bind=True)
def downgrade_workspace_to_free(self, workspace_id: str, reason: str):
    """
    Downgrade workspace to free tier (background cleanup).
    
    Args:
        workspace_id: Workspace ID
        reason: Downgrade reason
    """
    try:
        from services.b2c.middleware.subscription_guard import downgrade_to_free_tier
        
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        
        if not workspace:
            logger.error(f"Workspace not found: {workspace_id}")
            return
        
        # Perform downgrade
        downgrade_to_free_tier(self.db, workspace)
        
        # Send notification
        if workspace.owner_id:
            send_subscription_canceled_email.delay(
                user_id=str(workspace.owner_id),
                workspace_id=str(workspace_id),
                reason=reason
            )
        
        logger.info(f"Workspace {workspace_id} downgraded to free tier")
        
    except Exception as e:
        logger.error(f"Error downgrading workspace: {str(e)}")
        raise


@app.task(base=DatabaseTask, bind=True)
def check_grace_period_expirations(self):
    """
    Periodic task to check for expired grace periods and downgrade workspaces.
    
    Should be run daily via celery beat.
    """
    try:
        from datetime import datetime, timedelta
        
        # Find subscriptions in past_due status
        past_due_subscriptions = self.db.query(Subscription).filter(
            Subscription.status == 'past_due'
        ).all()
        
        grace_period_days = 7
        now = datetime.now()
        
        for subscription in past_due_subscriptions:
            if not subscription.current_period_end:
                continue
            
            grace_period_end = subscription.current_period_end + timedelta(days=grace_period_days)
            
            # Check if grace period expired
            if now > grace_period_end:
                logger.info(f"Grace period expired for subscription {subscription.id}")
                downgrade_workspace_to_free.delay(
                    workspace_id=str(subscription.workspace_id),
                    reason="payment_failed"
                )
            
            # Send reminders at 3 days and 1 day remaining
            days_remaining = (grace_period_end - now).days
            if days_remaining in [3, 1]:
                send_grace_period_expiring_email.delay(
                    user_id=str(subscription.user_id),
                    workspace_id=str(subscription.workspace_id),
                    days_remaining=days_remaining
                )
        
        logger.info(f"Checked {len(past_due_subscriptions)} past due subscriptions")
        
    except Exception as e:
        logger.error(f"Error checking grace periods: {str(e)}")
        raise
