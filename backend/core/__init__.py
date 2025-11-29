"""
Core package - shared utilities across all services.

This package uses a dual import strategy during migration:
- Imports from existing app.* modules
- Re-exports with core.* namespace
- Allows gradual migration of routers to use core.*
"""

# Config and Database (already copied to core/)
from core.config import settings, Settings
from core.database import (
    get_db,
    init_db,
    close_db,
    engine,
    AsyncSessionLocal,
    current_tenant_id,
)

# RBAC (re-exported from app.rbac)
from core.rbac import (
    require_permission,
    require_role,
    has_permission,
    get_user_permissions,
)

# Middleware (re-exported from app.middleware)
from core.middleware import (
    get_current_user,
)

__all__ = [
    # Config
    "settings",
    "Settings",
    # Database
    "get_db",
    "init_db",
    "close_db",
    "engine",
    "AsyncSessionLocal",
    "current_tenant_id",
    # RBAC
    "require_permission",
    "require_role",
    "has_permission",
    "get_user_permissions",
    # Middleware
    "get_current_user",
]
