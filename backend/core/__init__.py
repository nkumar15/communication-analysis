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

# Middleware (shared token decode)
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
    # Middleware
    "get_current_user",
]

