"""
RBAC Package

Exports all RBAC functionality.
"""
from .permission_checker import (
    has_permission,
    get_user_permissions,
    get_user_role_name
)
from .scope_checker import (
    get_accessible_user_ids,
    can_access_user,
    get_dashboard_stats,
    can_manage_team,
    get_user_team_ids,
    is_team_manager
)
from .decorators import (
    require_permission,
    require_role,
    require_permission_and_role
)

__all__ = [
    # Permission checkers
    'has_permission',
    'get_user_permissions',
    'get_user_role_name',
    
    # Scope helpers
    'get_accessible_user_ids',
    'can_access_user',
    'get_dashboard_stats',
    'can_manage_team',
    'get_user_team_ids',
    'is_team_manager',
    
    # Decorators
    'require_permission',
    'require_role',
    'require_permission_and_role',
]
