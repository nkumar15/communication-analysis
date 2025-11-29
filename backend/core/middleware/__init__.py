"""
Core Middleware Package

Re-exports authentication middleware from core and platform middleware.
"""

# Re-export from existing app.middleware
from .auth import get_current_user, get_current_active_user
from services.platform.middleware.platform_auth import verify_platform_admin, log_platform_action

__all__ = [
    "get_current_user",
    "get_current_active_user",
    "verify_platform_admin",
    "log_platform_action"
]
