"""
RBAC Package

Exports all RBAC functionality.
"""

# Import from existing app.rbac
from services.b2b.rbac.permission_checker import (
    has_permission,
    get_user_permissions,
    get_user_role_name
)
from services.b2b.rbac.scope_checker import (
    get_accessible_user_ids,
    get_accessible_farmers_query,
    can_access_farmer,
    can_access_user,
    get_dashboard_stats
)
from services.b2b.rbac.decorators import (
    require_permission,
    require_role,
    require_permission_and_role
)

# Re-export everything
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
