"""
B2B Middleware Package

Authentication and authorization middleware for B2B tenant users.
"""
from services.b2b.middleware.b2b_auth import get_current_active_user

__all__ = ["get_current_active_user"]
