"""
Firebase Custom Token Helper for E2E Tests

This module provides utilities to create Firebase custom tokens for automated testing.
Custom tokens allow bypassing the OAuth flow while still using real Firebase authentication.

Usage:
    from e2e_helpers import create_custom_token
    
    token = create_custom_token(
        uid="test-user-123",
        email="test@example.com",
        tenant_id="system-platform"
    )
"""
from firebase_admin import auth, credentials, initialize_app, _apps
from core.config import settings

def _ensure_firebase_initialized():
    """Ensure Firebase App is initialized"""
    if not _apps:
        cred = credentials.Certificate(settings.firebase_credentials_path_resolved)
        initialize_app(cred)

def create_custom_token(uid: str, email: str, tenant_id: str = None) -> str:
    """
    Create a Firebase custom token for testing.
    
    Args:
        uid: User ID
        email: User email
        tenant_id: Optional Firebase tenant ID
        
    Returns:
        Custom token string that can be used with signInWithCustomToken()
    """
    _ensure_firebase_initialized()
    additional_claims = {
        'email': email,
        'email_verified': True
    }
    
    # Create custom token (blocking call)
    if tenant_id:
        # For multi-tenancy, use the tenant-specific auth provider
        tenant_auth = auth.tenant_manager().auth_for_tenant(tenant_id)
        token = tenant_auth.create_custom_token(uid, additional_claims)
    else:
        # For standard (B2C/Global) auth
        token = auth.create_custom_token(uid, additional_claims)
    
    return token.decode('utf-8')


def create_platform_admin_token(email: str) -> str:
    """
    Create a custom token for a platform admin user.
    """
    from .e2e_config import SYSTEM_TENANT_ID
    return create_custom_token(
        uid=f"e2e-platform-{email}",
        email=email,
        tenant_id=SYSTEM_TENANT_ID
    )


def create_tenant_user_token(email: str, tenant_id: str) -> str:
    """
    Create a custom token for a tenant user.
    """
    return create_custom_token(
        uid=f"e2e-user-{email}",
        email=email,
        tenant_id=tenant_id
    )
