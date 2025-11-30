"""
Core Middleware Package

Shared authentication middleware for all services.
Service-specific auth logic lives in respective service middleware folders.
"""
from .auth import get_current_user

__all__ = ["get_current_user"]
