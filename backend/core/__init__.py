"""
Core package - shared utilities across all services.

This package uses a dual import strategy during migration:
- Imports from existing app.* modules
- Re-exports with core.* namespace
- Allows gradual migration of routers to use core.*
"""

# Config
from core.config import settings, Settings

# Database
from core.db import (
    get_db,
    init_db,
    close_db,
    engine,
    AsyncSessionLocal,
    current_tenant_id,
    Base,
    rls_service
)

# Middleware
from core.middleware import get_current_user

__all__ = [
    "settings",
    "Settings",
    "get_db",
    "init_db",
    "close_db",
    "engine",
    "AsyncSessionLocal",
    "current_tenant_id",
    "Base",
    "rls_service",
    "get_current_user",
]

