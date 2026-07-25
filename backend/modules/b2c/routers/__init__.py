"""B2C Routers Package"""
from .auth import router as auth_router
from .workspaces import router as workspaces_router
from .billing import router as billing_router
from .invitations import router as invitations_router

__all__ = [
    'auth_router',
    'workspaces_router',
    'billing_router',
    'invitations_router'
]
