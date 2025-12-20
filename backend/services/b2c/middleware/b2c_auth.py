"""B2C Authentication Middleware"""
from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.utils.firebase import firebase_auth_service
from services.b2c.models.user import B2CUser
from core.logging import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


async def get_current_b2c_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current B2C user from Firebase ID token
    
    Sets RLS context for workspace-scoped data isolation
    
    Returns dict with user fields including 'id', 'email', 'workspaces'
    """
    id_token = credentials.credentials
    
    try:
        # Verify Firebase token
        decoded_token = await firebase_auth_service.verify_id_token(id_token)
        firebase_uid = decoded_token.get('uid')
        email = decoded_token.get('email')
        
        if not firebase_uid or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing uid or email"
            )
        
    except Exception as e:
        logger.error("firebase_token_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Find user ID using Security Definer function (bypass RLS)
    from sqlalchemy import func
    user_id = await db.scalar(
        select(func.b2c.lookup_user_by_firebase_uid(firebase_uid))
    )
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please sign up first."
        )
    
    # Set RLS context FIRST so we can query the user object
    from core.rls import rls_service
    await rls_service.set_user_context(db, user_id)
    
    # Now fetch user details (RLS allowed)
    result = await db.execute(
        select(B2CUser).where(B2CUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Should not happen if lookup succeeded, unless deleted/race condition
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found"
        )
    
    # Check if user is deleted
    if user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found"
        )
        
    return {
        "id": user.id,
        "email": user.email,
        "firebase_uid": user.firebase_uid,
        "display_name": user.display_name,
        "personal_workspace_id": user.default_workspace_id
    }


async def get_current_b2c_user_optional(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> Dict[str, Any] | None:
    """Optional authentication - returns None if not authenticated"""
    if not credentials:
        return None
    
    try:
        return await get_current_b2c_user(credentials, db)
    except HTTPException:
        return None
