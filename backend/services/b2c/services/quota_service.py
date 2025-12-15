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

TIER_LIMITS = {
    'free': {
        'max_projects': 5,
        'max_team_workspaces': 0,
        'max_storage_gb': 1,
        'max_team_members': 2,  # Shareable links only, viewer access
        'features': {
            'team_workspaces': False,
            'priority_support': False,
            'custom_branding': False,
            'export_data': False,
            'sso': False,
            'api_access': False,
            'audit_logs': False
        }
    },
    'premium': {
        'max_projects': None,  # Unlimited
        'max_team_workspaces': 3,
        'max_storage_gb': 10,
        'max_team_members': 10,
        'features': {
            'team_workspaces': True,
            'priority_support': True,
            'custom_branding': True,
            'export_data': True,
            'sso': False,
            'api_access': False,
            'audit_logs': False
        }
    },
    'ultimate': {
        'max_projects': None,  # Unlimited
        'max_team_workspaces': None,  # Unlimited
        'max_storage_gb': 100,
        'max_team_members': None,  # Unlimited
        'features': {
            'team_workspaces': True,
            'priority_support': True,
            'custom_branding': True,
            'export_data': True,
            'sso': True,
            'api_access': True,
            'audit_logs': True
        }
    }
}


# ============================================================================
# Exceptions
# ============================================================================

class QuotaExceededError(Exception):
    """Raised when a quota limit is exceeded."""
    
    def __init__(self, message: str, tier: str, limit_type: str, current: int, max_allowed: Optional[int]):
        self.message = message
        self.tier = tier
        self.limit_type = limit_type
        self.current = current
        self.max_allowed = max_allowed
        super().__init__(self.message)


class FeatureNotAvailableError(Exception):
    """Raised when a feature is not available for the current tier."""
    
    def __init__(self, message: str, tier: str, feature: str, required_tier: str):
        self.message = message
        self.tier = tier
        self.feature = feature
        self.required_tier = required_tier
        super().__init__(self.message)


# ============================================================================
# Quota Service
# ============================================================================

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
    
    def get_tier_limits(self, tier: str) -> dict:
        """Get limits for a specific tier."""
        return TIER_LIMITS.get(tier, TIER_LIMITS['free'])
    
    def check_project_limit(self, workspace: Workspace, current_count: Optional[int] = None) -> None:
        """
        Check if workspace can create more projects.
        
        Args:
            workspace: Workspace to check
            current_count: Current project count (optional, will query if not provided)
            
        Raises:
            QuotaExceededError: If project limit exceeded
        """
        tier = self.get_workspace_tier(workspace)
        limits = self.get_tier_limits(tier)
        max_projects = limits['max_projects']
        
        # Unlimited projects
        if max_projects is None:
            return
        
        # Get current count if not provided
        if current_count is None:
            # This would require importing project model - placeholder for now
            # from backend.services.b2c.models.project import Project
            # current_count = self.db.query(Project).filter(
            #     Project.workspace_id == workspace.id,
            #     Project.deleted_at.is_(None)
            # ).count()
            current_count = 0  # Placeholder
        
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
        
        Args:
            user: User to check
            current_count: Current team workspace count (optional)
            
        Raises:
            QuotaExceededError: If team workspace limit exceeded
            FeatureNotAvailableError: If team workspaces not available for tier
        """
        # Get user's subscription from their personal workspace
        personal_workspace = self.db.query(Workspace).filter(
            Workspace.owner_id == user.id,
            Workspace.type == 'personal'
        ).first()
        
        if not personal_workspace:
            raise ValueError("User has no personal workspace")
        
        tier = self.get_workspace_tier(personal_workspace)
        limits = self.get_tier_limits(tier)
        
        # Check if feature is available
        if not limits['features']['team_workspaces']:
            raise FeatureNotAvailableError(
                message=f"Team workspaces are not available on the {tier} plan. Upgrade to Premium or Ultimate.",
                tier=tier,
                feature='team_workspaces',
                required_tier='premium'
            )
        
        max_team_workspaces = limits['max_team_workspaces']
        
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
        
        Args:
            workspace: Workspace to check
            current_count: Current member count (optional)
            
        Raises:
            QuotaExceededError: If member limit exceeded
        """
        tier = self.get_workspace_tier(workspace)
        limits = self.get_tier_limits(tier)
        max_members = limits['max_team_members']
        
        # Unlimited members
        if max_members is None:
            return
        
        # Get current count if not provided
        if current_count is None:
            # Placeholder - would need WorkspaceMember model
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
        
        Args:
            workspace: Workspace to check
            feature: Feature name (e.g., 'custom_branding', 'sso', 'api_access')
            
        Raises:
            FeatureNotAvailableError: If feature not available
        """
        tier = self.get_workspace_tier(workspace)
        limits = self.get_tier_limits(tier)
        
        if not limits['features'].get(feature, False):
            # Determine required tier
            required_tier = 'premium'
            for t in ['premium', 'ultimate']:
                if TIER_LIMITS[t]['features'].get(feature):
                    required_tier = t
                    break
            
            raise FeatureNotAvailableError(
                message=f"Feature '{feature}' is not available on the {tier} plan. Upgrade to {required_tier.capitalize()}.",
                tier=tier,
                feature=feature,
                required_tier=required_tier
            )


# ============================================================================
# Decorator for Quota Enforcement
# ============================================================================

def enforce_quota(limit_type: str):
    """
    Decorator to enforce quota limits on endpoint handlers.
    
    Usage:
        @enforce_quota('projects')
        async def create_project(...):
            ...
    
    Args:
        limit_type: Type of quota to check ('projects', 'team_workspaces', 'team_members')
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
    
    Usage:
        @require_feature('custom_branding')
        async def update_branding(...):
            ...
    
    Args:
        feature: Feature name to check
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
