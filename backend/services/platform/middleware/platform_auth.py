"""
Platform Admin Authentication Middleware

This module provides authentication and authorization for platform administrators.
Platform admins are stored in a SEPARATE table from customer tenant users
for security isolation.

IMPORTANT: This middleware checks the platform_admins table, NOT the users table.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.utils.firebase import firebase_auth_service
from services.platform.models import PlatformUser, PlatformRole, PlatformAuditLog
from core.utils import get_utc_now
from core.database import get_db
from datetime import datetime
from typing import Optional


from core.middleware.auth import get_current_user

async def verify_platform_admin(
    decoded_token: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Verify that the authenticated user is a platform admin.
    
    This middleware:
    1. Validates Firebase JWT token (via get_current_user)
    2. Checks platform_users table (NOT users table)
    3. Updates last_login_at timestamp
    4. Returns platform admin details
    
    Args:
        decoded_token: Decoded JWT token from get_current_user dependency
        db: Database session
        
    Returns:
        dict: Platform admin details {id, email, role, firebase_uid, tenant_id}
        
    Raises:
        HTTPException: 401 if token invalid, 403 if not a platform admin
    """
    firebase_uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    
    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    # Check platform_users table (NOT users table)
    # Join with PlatformRole to get the role name
    result = await db.execute(
        select(PlatformUser, PlatformRole)
        .join(PlatformRole, PlatformUser.platform_role_id == PlatformRole.id)
        .where(PlatformUser.firebase_uid == firebase_uid)
        .where(PlatformUser.is_active == True)
    )
    user_role_pair = result.first()
    
    if not user_role_pair:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Platform administrator privileges required."
        )
    
    platform_user, platform_role = user_role_pair
    
    # Update last login timestamp
    platform_user.last_login_at = get_utc_now()
    await db.commit()
    
    return {
        "id": str(platform_user.id),
        "email": platform_user.email,
        "role": platform_role.name,
        "display_name": platform_user.display_name,
        "firebase_uid": platform_user.firebase_uid,
        "tenant_id": str(platform_user.platform_tenant_id)
    }


async def log_platform_action(
    admin: dict,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    db: AsyncSession = None
):
    """
    Log a platform admin action to the audit log.
    
    Args:
        admin: Platform admin dict from verify_platform_admin
        action: Action performed (e.g., "create_tenant", "delete_user")
        resource_type: Type of resource affected (e.g., "tenant", "user")
        resource_id: ID of the affected resource
        details: Additional details as dict (will be stored as JSON string)
        ip_address: IP address of the request
        user_agent: User agent string
        db: Database session
    """
    if not db:
        return  # Can't log without DB session
    

    
    audit_entry = PlatformAuditLog(
        platform_tenant_id=admin["tenant_id"],
        user_id=admin["id"],
        user_email=admin["email"],
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details, # SQLAlchemy handles JSONB conversion for dicts usually, but let's check
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(audit_entry)
    await db.commit()


# Helper to get client IP from request
def get_client_ip(request) -> str:
    """Extract client IP address from request headers."""
    # Check X-Forwarded-For header (if behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client
    return request.client.host if request.client else "unknown"
