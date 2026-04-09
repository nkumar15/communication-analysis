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
    get_dashboard_stats,
    can_manage_team,
    get_user_team_ids,
    is_team_manager
)
from .decorators import (
    require_permission,
    require_role
)

__all__ = [
    'has_permission',
    'get_user_permissions',
    'get_user_role_name',
    'get_accessible_user_ids',
    'get_dashboard_stats',
    'can_manage_team',
    'get_user_team_ids',
    'is_team_manager',
    'require_permission',
    'require_role',
]
