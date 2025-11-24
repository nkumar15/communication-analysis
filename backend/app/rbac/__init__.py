"""
RBAC Package

Exports all RBAC functionality.
"""
from app.rbac.permission_checker import (
    has_permission,
    get_user_permissions,
    get_user_role_name
)
from app.rbac.scope_checker import (
    get_accessible_user_ids,
    get_accessible_farmers_query,
    can_access_farmer,
    can_access_user,
    get_dashboard_stats
)
from app.rbac.decorators import (
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
    'get_accessible_farmers_query',
    'can_access_farmer',
    'can_access_user',
    'get_dashboard_stats',
    
    # Decorators
    'require_permission',
    'require_role',
    'require_permission_and_role',
]
