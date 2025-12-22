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
    """
    try:
        from infrastructure.email.service import email_service
        
        user = self.db.query(B2CUser).filter(B2CUser.id == user_id).first()
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        
        if not user or not workspace:
            logger.error(f"User or workspace not found: {user_id}, {workspace_id}")
            return
        
        subscription = self.db.query(Subscription).filter(
            Subscription.workspace_id == workspace_id
        ).first()
        
        subject = "Payment Failed - Action Required"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #ef4444;">Payment Failed</h2>
                    <p>Hi {user.display_name or user.email},</p>
                    <p>We were unable to process the payment for your workspace <strong>{workspace.name}</strong>.</p>
                    <p>To avoid service interruption, please update your payment method within <strong>{grace_period_days} days</strong>.</p>
                    <p>
                        <a href="{settings.frontend_url}/billing" 
                           style="background: #ef4444; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                           Update Payment Method
                        </a>
                    </p>
                </div>
            </body>
        </html>
        """
        
        email_service.provider.send(user.email, subject, html_content)
        logger.info(f"Payment failure email sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Error sending payment failure email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@app.task(base=DatabaseTask, bind=True, max_retries=3)
def send_subscription_canceled_email(self, user_id: str, workspace_id: str, reason: str = "user_request"):
    """
    Send email when subscription is canceled.
    """
    try:
        from infrastructure.email.service import email_service

        user = self.db.query(B2CUser).filter(B2CUser.id == user_id).first()
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        
        if not user or not workspace:
            return
        
        subscription = self.db.query(Subscription).filter(
            Subscription.workspace_id == workspace_id
        ).first()
        
        subject = "Subscription Canceled"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>Subscription Canceled</h2>
                    <p>Hi {user.display_name or user.email},</p>
                    <p>Your subscription for workspace <strong>{workspace.name}</strong> has been canceled.</p>
                    <p>Reason: {reason}</p>
                    <p>You can reactivate your subscription at any time.</p>
                    <p>
                        <a href="{settings.frontend_url}/pricing" 
                           style="background: #4F46E5; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                           View Plans
                        </a>
                    </p>
                </div>
            </body>
        </html>
        """
        
        email_service.provider.send(user.email, subject, html_content)
        logger.info(f"Subscription canceled email sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Error sending cancellation email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@app.task(base=DatabaseTask, bind=True, max_retries=3)
def send_subscription_activated_email(self, user_id: str, workspace_id: str):
    """
    Send welcome email when subscription is activated.
    """
    try:
        from infrastructure.email.service import email_service

        user = self.db.query(B2CUser).filter(B2CUser.id == user_id).first()
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        
        if not user or not workspace:
            return
        
        subscription = self.db.query(Subscription).filter(
            Subscription.workspace_id == workspace_id
        ).first()

        tier = subscription.tier.capitalize()
        subject = f"Welcome to {tier}!"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4F46E5;">Welcome to {tier}!</h2>
                    <p>Hi {user.display_name or user.email},</p>
                    <p>Thank you for subscribing to the <strong>{workspace.name}</strong> workspace.</p>
                    <p>You now have access to all {tier} features.</p>
                    <p>
                        <a href="{settings.frontend_url}/dashboard" 
                           style="background: #4F46E5; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                           Go to Dashboard
                        </a>
                    </p>
                </div>
            </body>
        </html>
        """
        
        email_service.provider.send(user.email, subject, html_content)
        logger.info(f"Subscription activated email sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Error sending activation email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@app.task(base=DatabaseTask, bind=True, max_retries=3)
def send_invoice_payment_succeeded_email(self, user_id: str, invoice_id: str):
    """
    Send receipt email when invoice is paid.
    """
    try:
        from services.b2c.models.subscription import Invoice
        from infrastructure.email.service import email_service
        
        user = self.db.query(B2CUser).filter(B2CUser.id == user_id).first()
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        
        if not user or not invoice:
            return
            
        subject = "Payment Receipt"
        amount = f"${invoice.amount_paid / 100:.2f}"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>Payment Receipt</h2>
                    <p>Hi {user.display_name or user.email},</p>
                    <p>We received your payment of <strong>{amount}</strong>.</p>
                    <p>Date: {invoice.invoice_date.strftime("%B %d, %Y") if invoice.invoice_date else 'N/A'}</p>
                    <p>
                        <a href="{invoice.invoice_pdf_url}" 
                           style="background: #4F46E5; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                           Download Invoice
                        </a>
                    </p>
                </div>
            </body>
        </html>
        """
        
        email_service.provider.send(user.email, subject, html_content)
        logger.info(f"Invoice receipt sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Error sending invoice email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@app.task(base=DatabaseTask, bind=True, max_retries=3)
def send_grace_period_expiring_email(self, user_id: str, workspace_id: str, days_remaining: int):
    """
    Send reminder email when grace period is expiring.
    """
    try:
        from infrastructure.email.service import email_service
        
        user = self.db.query(B2CUser).filter(B2CUser.id == user_id).first()
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        
        if not user or not workspace:
            return
            
        subject = f"Payment Required - {days_remaining} Days Remaining"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #ef4444;">Action Required</h2>
                    <p>Hi {user.display_name or user.email},</p>
                    <p>This is a reminder that your payment for <strong>{workspace.name}</strong> is overdue.</p>
                    <p>Your subscription will be downgraded in <strong>{days_remaining} days</strong>.</p>
                    <p>
                        <a href="{settings.frontend_url}/billing" 
                           style="background: #ef4444; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                           Update Payment Method
                        </a>
                    </p>
                </div>
            </body>
        </html>
        """
        
        email_service.provider.send(user.email, subject, html_content)
        logger.info(f"Grace period reminder sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Error sending grace period email: {str(e)}")
        raise self.retry(exc=e, countdown=60)


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
    Send workspace invitation email.
    """
    try:
        from infrastructure.email.service import email_service
        
        b2c_frontend_url = settings.frontend_url_b2c or settings.frontend_url
        invitation_url = f"{b2c_frontend_url}/invite/{invitation_token}"
        subject = f"You've been invited to join {workspace_name}"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4F46E5;">You've been invited!</h2>
                    <p>Hi,</p>
                    <p><strong>{inviter_name}</strong> has invited you to join <strong>{workspace_name}</strong> as a {role}.</p>
                    <p>
                        <a href="{invitation_url}" 
                           style="background: #4F46E5; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                           Accept Invitation
                        </a>
                    </p>
                    <p><small>Link: {invitation_url}</small></p>
                </div>
            </body>
        </html>
        """
        
        email_service.provider.send(invitee_email, subject, html_content)
        logger.info(f"Workspace invitation email sent to {invitee_email}")
        
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
