"""
Quota Enforcement Service

Enforces subscription tier limits on resources and features.
"""
from sqlalchemy.orm import Session
from functools import wraps
from typing import Callable, Optional
from fastapi import HTTPException
import logging

from services.b2c.models.subscription import Subscription
from services.b2c.models.workspace import Workspace
from services.b2c.models.user import B2CUser

logger = logging.getLogger(__name__)


# ============================================================================
# Tier Limits Configuration
# ============================================================================

from services.b2c.models.subscription_plan import SubscriptionPlan

class QuotaService:
    """
    Service for checking and enforcing subscription quota limits.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_workspace_tier(self, workspace: Workspace) -> str:
        """Get the subscription tier for a workspace."""
        subscription = self.db.query(Subscription).filter(
            Subscription.workspace_id == workspace.id
        ).first()
        
        if not subscription or subscription.status not in ['active', 'trialing']:
            return 'free'
        
        return subscription.tier
    
    def get_tier_plan(self, tier: str) -> SubscriptionPlan:
        """Get plan configuration for a specific tier."""
        plan = self.db.query(SubscriptionPlan).filter(
            SubscriptionPlan.tier == tier
        ).first()
        
        if not plan:
            # Fallback to free plan if tier not found
            # This handles cases where a legacy tier might be removed
            logger.warning(f"Plan for tier '{tier}' not found, falling back to free")
            plan = self.db.query(SubscriptionPlan).filter(
                SubscriptionPlan.tier == 'free'
            ).first()
            
        if not plan:
             # Extreme fallback if even free plan is missing (should not happen after seed)
             # Return a minimal default object to prevent crash
            logger.error("Critial: Free plan not found in database")
            return SubscriptionPlan(
                tier='free',
                limits={
                    'projects': 5,
                    'team_workspaces': 1,
                    'storage_gb': 1,
                    'team_members': 2
                },
                features={} 
            )
            
        return plan
    
    def check_project_limit(self, workspace: Workspace, current_count: Optional[int] = None) -> None:
        """
        Check if workspace can create more projects.
        """
        tier = self.get_workspace_tier(workspace)
        plan = self.get_tier_plan(tier)
        max_projects = plan.limits.get('projects')
        
        # Unlimited projects
        if max_projects is None:
            return
        
        # Get current count if not provided
        if current_count is None:
            # Placeholder for actual project count logic
            current_count = 0 
        
        if current_count >= max_projects:
            raise QuotaExceededError(
                message=f"Project limit exceeded. Your {tier} plan allows {max_projects} projects.",
                tier=tier,
                limit_type='projects',
                current=current_count,
                max_allowed=max_projects
            )
    
    def check_team_workspace_limit(self, user: B2CUser, current_count: Optional[int] = None) -> None:
        """
        Check if user can create more team workspaces.
        """
        # Get user's subscription from their personal workspace
        personal_workspace = self.db.query(Workspace).filter(
            Workspace.owner_id == user.id,
            Workspace.type == 'personal'
        ).first()
        
        if not personal_workspace:
            raise ValueError("User has no personal workspace")
        
        tier = self.get_workspace_tier(personal_workspace)
        plan = self.get_tier_plan(tier)
        
        # Check if feature is available
        if not plan.features.get('team_workspaces', False):
             raise FeatureNotAvailableError(
                message=f"Team workspaces are not available on the {tier} plan.",
                tier=tier,
                feature='team_workspaces',
                required_tier='premium' # simplified
            )
        
        max_team_workspaces = plan.limits.get('team_workspaces')
        
        # Unlimited team workspaces
        if max_team_workspaces is None:
            return
        
        # Get current count if not provided
        if current_count is None:
            current_count = self.db.query(Workspace).filter(
                Workspace.owner_id == user.id,
                Workspace.type == 'team'
            ).count()
        
        if current_count >= max_team_workspaces:
            raise QuotaExceededError(
                message=f"Team workspace limit exceeded. Your {tier} plan allows {max_team_workspaces} team workspaces.",
                tier=tier,
                limit_type='team_workspaces',
                current=current_count,
                max_allowed=max_team_workspaces
            )
    
    def check_team_member_limit(self, workspace: Workspace, current_count: Optional[int] = None) -> None:
        """
        Check if workspace can add more team members.
        """
        tier = self.get_workspace_tier(workspace)
        plan = self.get_tier_plan(tier)
        max_members = plan.limits.get('team_members')
        
        # Unlimited members
        if max_members is None:
            return
        
        # Get current count if not provided
        if current_count is None:
            # Placeholder
            current_count = 0
        
        if current_count >= max_members:
            raise QuotaExceededError(
                message=f"Team member limit exceeded. Your {tier} plan allows {max_members} members.",
                tier=tier,
                limit_type='team_members',
                current=current_count,
                max_allowed=max_members
            )
    
    def check_feature_access(self, workspace: Workspace, feature: str) -> None:
        """
        Check if a feature is available for the workspace's tier.
        """
        tier = self.get_workspace_tier(workspace)
        plan = self.get_tier_plan(tier)
        
        if not plan.features.get(feature, False):
            raise FeatureNotAvailableError(
                message=f"Feature '{feature}' is not available on the {tier} plan.",
                tier=tier,
                feature=feature,
                required_tier='premium' # Simplified logic
            )


# ============================================================================
# Decorator for Quota Enforcement
# ============================================================================

def enforce_quota(limit_type: str):
    """
    Decorator to enforce quota limits on endpoint handlers.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract workspace and db from function arguments
            workspace = kwargs.get('workspace')
            user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not db:
                raise ValueError("Database session not found in function arguments")
            
            quota_service = QuotaService(db)
            
            try:
                if limit_type == 'projects':
                    if not workspace:
                        raise ValueError("Workspace not found in function arguments")
                    quota_service.check_project_limit(workspace)
                
                elif limit_type == 'team_workspaces':
                    if not user:
                        raise ValueError("User not found in function arguments")
                    quota_service.check_team_workspace_limit(user)
                
                elif limit_type == 'team_members':
                    if not workspace:
                        raise ValueError("Workspace not found in function arguments")
                    quota_service.check_team_member_limit(workspace)
                
                else:
                    raise ValueError(f"Unknown limit type: {limit_type}")
                
            except QuotaExceededError as e:
                logger.warning(f"Quota exceeded: {e.message}")
                raise HTTPException(
                    status_code=402,  # Payment Required
                    detail={
                        'error': 'quota_exceeded',
                        'message': e.message,
                        'tier': e.tier,
                        'limit_type': e.limit_type,
                        'current': e.current,
                        'max_allowed': e.max_allowed
                    }
                )
            
            except FeatureNotAvailableError as e:
                logger.warning(f"Feature not available: {e.message}")
                raise HTTPException(
                    status_code=403,  # Forbidden
                    detail={
                        'error': 'feature_not_available',
                        'message': e.message,
                        'tier': e.tier,
                        'feature': e.feature,
                        'required_tier': e.required_tier
                    }
                )
            
            # Call the original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_feature(feature: str):
    """
    Decorator to check if a feature is available for the workspace.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            workspace = kwargs.get('workspace')
            db = kwargs.get('db')
            
            if not workspace or not db:
                raise ValueError("Workspace and database session required")
            
            quota_service = QuotaService(db)
            
            try:
                quota_service.check_feature_access(workspace, feature)
            except FeatureNotAvailableError as e:
                logger.warning(f"Feature access denied: {e.message}")
                raise HTTPException(
                    status_code=403,
                    detail={
                        'error': 'feature_not_available',
                        'message': e.message,
                        'tier': e.tier,
                        'feature': e.feature,
                        'required_tier': e.required_tier
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# Async Quota Service (for use with AsyncSession)
# ============================================================================

class AsyncQuotaService:
    """Async version of QuotaService for use with AsyncSession"""
    
    async def get_tier_plan(self, db, tier: str) -> SubscriptionPlan:
        """Get plan configuration for a specific tier (async)."""
        from sqlalchemy import select
        
        result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.tier == tier))
        plan = result.scalar_one_or_none()
        
        if not plan:
            result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.tier == 'free'))
            plan = result.scalar_one_or_none()
            
        if not plan:
            return SubscriptionPlan(
                tier='free',
                limits={
                    'projects': 5,
                    'team_workspaces': 1,
                    'storage_gb': 1,
                    'team_members': 2
                },
                features={}
            )
        return plan

    async def check_team_workspace_limit(
        self,
        db,
        user_id: str,
        subscription_tier: str
    ) -> tuple[bool, str]:
        """
        Check if user can create more team workspaces (async)
        """
        from sqlalchemy import select, func
        
        plan = await self.get_tier_plan(db, subscription_tier)
        
        # Check if feature is available
        if not plan.features.get('team_workspaces', False):
            return False, f"Team workspaces require Premium or Ultimate subscription"
        
        max_team_workspaces = plan.limits.get('team_workspaces')
        
        # Unlimited team workspaces
        if max_team_workspaces is None:
            return True, "Unlimited workspaces"
        
        # Count current team workspaces
        result = await db.execute(
            select(func.count()).select_from(Workspace).where(
                Workspace.owner_id == user_id,
                Workspace.type == 'team'
            )
        )
        current_count = result.scalar() or 0
        
        if current_count >= max_team_workspaces:
            return False, f"Limit reached: {current_count}/{max_team_workspaces} team workspaces"
        
        return True, f"Can create {max_team_workspaces - current_count} more team workspaces"


# Singleton
quota_service = AsyncQuotaService()
