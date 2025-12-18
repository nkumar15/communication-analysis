"""
Subscription Status Enforcement

Middleware and decorators to restrict access based on subscription payment status.
"""
from sqlalchemy.orm import Session
from functools import wraps
from typing import Callable
from fastapi import HTTPException
from datetime import datetime, timedelta
import logging

from services.b2c.models.subscription import Subscription
from services.b2c.models.workspace import Workspace
from services.b2c.models.user import B2CUser

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

# Grace period after payment failure before restricting access
GRACE_PERIOD_DAYS = 7

# Statuses that allow access
ALLOWED_STATUSES = ['active', 'trialing']

# Statuses that trigger grace period (limited access)
GRACE_PERIOD_STATUSES = ['past_due']

# Statuses that completely block access
BLOCKED_STATUSES = ['canceled', 'incomplete', 'incomplete_expired', 'unpaid']


# ============================================================================
# Exceptions
# ============================================================================

class SubscriptionRequiredError(Exception):
    """Raised when subscription is required but not active."""
    
    def __init__(self, message: str, status: str, grace_period_ends: datetime = None):
        self.message = message
        self.status = status
        self.grace_period_ends = grace_period_ends
        super().__init__(self.message)


class PaymentFailedError(Exception):
    """Raised when payment has failed and grace period expired."""
    
    def __init__(self, message: str, status: str):
        self.message = message
        self.status = status
        super().__init__(self.message)


# ============================================================================
# Subscription Status Checker
# ============================================================================

class SubscriptionStatusChecker:
    """
    Service to check and enforce subscription status requirements.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_workspace_access(
        self,
        workspace: Workspace,
        require_paid: bool = True
    ) -> tuple[bool, str, dict]:
        """
        Check if workspace has valid subscription for access.
        
        Args:
            workspace: Workspace to check
            require_paid: If True, require paid subscription. If False, allow free tier.
            
        Returns:
            (allowed: bool, reason: str, details: dict)
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.workspace_id == workspace.id
        ).first()
        
        # No subscription = free tier
        if not subscription:
            if require_paid:
                return False, "paid_subscription_required", {
                    "message": "This feature requires a paid subscription",
                    "current_tier": "free",
                    "required_tier": "premium"
                }
            return True, "free_tier", {}
        
        status = subscription.status
        
        # Active or trialing = full access
        if status in ALLOWED_STATUSES:
            return True, status, {}
        
        # Past due = grace period check
        if status in GRACE_PERIOD_STATUSES:
            grace_period_ends = subscription.current_period_end + timedelta(days=GRACE_PERIOD_DAYS)
            
            if datetime.now() < grace_period_ends:
                # Still in grace period - allow access with warning
                return True, "grace_period", {
                    "message": "Your payment failed. Please update your payment method to continue service.",
                    "grace_period_ends": grace_period_ends.isoformat(),
                    "days_remaining": (grace_period_ends - datetime.now()).days
                }
            else:
                # Grace period expired - block access
                return False, "grace_period_expired", {
                    "message": "Your subscription is past due. Please update your payment method to restore access.",
                    "status": status,
                    "period_ended": subscription.current_period_end.isoformat()
                }
        
        # Canceled or other blocked statuses
        if status in BLOCKED_STATUSES:
            return False, status, {
                "message": f"Your subscription is {status}. Please renew to continue using this service.",
                "status": status,
                "tier": subscription.tier
            }
        
        # Unknown status - be conservative and block
        logger.warning(f"Unknown subscription status: {status}")
        return False, "unknown_status", {
            "message": "Unable to verify subscription status. Please contact support.",
            "status": status
        }
    
    def check_user_access(
        self,
        user: B2CUser,
        require_paid: bool = True
    ) -> tuple[bool, str, dict]:
        """
        Check if user has valid subscription (via personal workspace).
        
        Args:
            user: User to check
            require_paid: If True, require paid subscription
            
        Returns:
            (allowed: bool, reason: str, details: dict)
        """
        # Get user's personal workspace
        workspace = self.db.query(Workspace).filter(
            Workspace.owner_id == user.id,
            Workspace.type == 'personal'
        ).first()
        
        if not workspace:
            return False, "no_workspace", {
                "message": "User workspace not found"
            }
        
        return self.check_workspace_access(workspace, require_paid)
    
    def get_subscription_status_message(self, workspace: Workspace) -> dict:
        """
        Get human-readable subscription status message.
        """
        allowed, reason, details = self.check_workspace_access(workspace, require_paid=False)
        
        subscription = self.db.query(Subscription).filter(
            Subscription.workspace_id == workspace.id
        ).first()
        
        if not subscription:
            return {
                "status": "free",
                "message": "Free tier",
                "upgrade_recommended": True
            }
        
        tier_key = subscription.plan.tier_key if subscription.plan else 'free'
        
        if reason in ALLOWED_STATUSES:
            return {
                "status": subscription.status,
                "tier": tier_key,
                "message": f"Active {tier_key} subscription",
                "period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None
            }
        
        if reason == "grace_period":
            return {
                "status": "warning",
                "message": details["message"],
                "grace_period_ends": details["grace_period_ends"],
                "action_required": True
            }
        
        return {
            "status": "blocked",
            "message": details.get("message", "Subscription issue"),
            "action_required": True
        }


# ============================================================================
# Decorators
# ============================================================================

def require_active_subscription(require_paid: bool = True):
    """
    Decorator to require active subscription for endpoint access.
    
    Usage:
        @require_active_subscription(require_paid=True)
        async def premium_feature(...):
            ...
    
    Args:
        require_paid: If True, require paid subscription. If False, allow free tier.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            workspace = kwargs.get('workspace')
            current_user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not db:
                raise ValueError("Database session required")
            
            checker = SubscriptionStatusChecker(db)
            
            # Check workspace if provided, otherwise check user's personal workspace
            if workspace:
                allowed, reason, details = checker.check_workspace_access(workspace, require_paid)
            elif current_user:
                allowed, reason, details = checker.check_user_access(current_user, require_paid)
            else:
                raise ValueError("Either workspace or current_user required")
            
            if not allowed:
                logger.warning(f"Access denied due to subscription status: {reason}")
                raise HTTPException(
                    status_code=402,  # Payment Required
                    detail={
                        'error': 'subscription_required',
                        'reason': reason,
                        **details
                    }
                )
            
            # If in grace period, add warning to response (handled by middleware)
            if reason == 'grace_period':
                # You could add this to request context for display in UI
                logger.info(f"User in grace period: {details}")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_paid_subscription():
    """
    Decorator shorthand for requiring paid subscription.
    
    Usage:
        @require_paid_subscription()
        async def premium_only_feature(...):
            ...
    """
    return require_active_subscription(require_paid=True)


# ============================================================================
# Helper Functions
# ============================================================================

def downgrade_to_free_tier(db: Session, workspace: Workspace) -> None:
    """
    Downgrade workspace to free tier after subscription cancellation.
    """
    subscription = db.query(Subscription).filter(
        Subscription.workspace_id == workspace.id
    ).first()
    
    if subscription:
        from services.b2c.models.subscription_plan import SubscriptionPlan
        # Find active free plan
        free_plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.tier_key == 'free',
            SubscriptionPlan.archived_at.is_(None)
        ).order_by(SubscriptionPlan.effective_from.desc()).first()
        
        if free_plan:
             subscription.plan_id = free_plan.id
        
        subscription.status = 'canceled'
        db.commit()
        
        logger.info(f"Workspace {workspace.id} downgraded to free tier")
    
    # TODO: Additional cleanup:
    # - Notify workspace owner via email
    # - Archive/delete team workspaces beyond free limit
    # - Archive projects beyond free limit
    # - Disable premium features


def send_payment_failure_notification(db: Session, workspace: Workspace) -> None:
    """
    Send email notification about payment failure.
    
    Args:
        db: Database session
        workspace: Workspace with failed payment
    """
    # TODO: Implement email notification
    # - Send email to workspace owner
    # - Include grace period information
    # - Link to update payment method
    # - Explain consequences of non-payment
    
    logger.info(f"Payment failure notification sent for workspace {workspace.id}")
