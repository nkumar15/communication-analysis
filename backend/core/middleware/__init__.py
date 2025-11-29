"""
Core Middleware Package

Re-exports authentication middleware from core and platform middleware.
"""

# Re-export from existing app.middleware
from .auth import get_current_user, get_current_active_user

__all__ = [
    "get_current_user",
    "get_current_active_user",
]
