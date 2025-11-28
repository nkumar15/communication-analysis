"""
Firebase Custom Token Helper for E2E Tests

This module provides utilities to create Firebase custom tokens for automated testing.
Custom tokens allow bypassing the OAuth flow while still using real Firebase authentication.

Usage:
    from e2e_helpers import create_test_token
    
    token = await create_test_token(
        uid="test-user-123",
        email="test@example.com",
        tenant_id="system-platform"
    )
"""
from firebase_admin import auth
import asyncio

async def create_custom_token(uid: str, email: str, tenant_id: str = None) -> str:
    """
    Create a Firebase custom token for testing.
    
    Args:
        uid: User ID
        email: User email
        tenant_id: Optional Firebase tenant ID
        
    Returns:
        Custom token string that can be used with signInWithCustomToken()
    """
    additional_claims = {
        'email': email,
        'email_verified': True
    }
    
    # Create custom token (blocking call, run in executor)
    loop = asyncio.get_event_loop()
    token = await loop.run_in_executor(
        None,
        lambda: auth.create_custom_token(uid, additional_claims, tenant_id=tenant_id)
    )
    
    return token.decode('utf-8')


async def create_platform_admin_token(email: str) -> str:
    """
    Create a custom token for a platform admin user.
    
    Args:
        email: Platform admin email
        
    Returns:
        Custom token for the platform admin
    """
    from e2e_config import SYSTEM_TENANT_ID
    return await create_custom_token(
        uid=f"e2e-platform-{email}",
        email=email,
        tenant_id=SYSTEM_TENANT_ID
    )


async def create_tenant_user_token(email: str, tenant_id: str) -> str:
    """
    Create a custom token for a tenant user.
    
    Args:
        email: User email
        tenant_id: Firebase tenant ID
        
    Returns:
        Custom token for the tenant user
    """
    return await create_custom_token(
        uid=f"e2e-user-{email}",
        email=email,
        tenant_id=tenant_id
    )
