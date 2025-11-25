from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
from app.services.firebase_auth import firebase_auth_service


# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> Dict[str, Any]:
    """
    Get current user from Firebase ID token
    
    Args:
        credentials: Bearer token from Authorization header
        
    Returns:
        Decoded token with user information
        
    Raises:
        HTTPException: If not authenticated or token is invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Verify Firebase ID token
        decoded_token = await firebase_auth_service.verify_id_token(credentials.credentials)
        return decoded_token
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_auth(request: Request) -> Dict[str, Any]:
    """
    Require authentication (backward compatible wrapper)
    
    Args:
        request: FastAPI request
        
    Returns:
        Decoded token data
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        decoded_token = await firebase_auth_service.verify_id_token(token)
        return decoded_token
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


# Import here to avoid circular imports if possible, or use string forward refs if needed
# But get_db needs to be imported.
from app.database import get_db, current_tenant_id
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db_models import UserModel

async def get_current_active_user(
    decoded_token: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current user from database using Firebase ID token
    
    Also sets the tenant context for Row Level Security enforcement.
    
    Returns dict with user fields including 'id'
    """
    firebase_uid = decoded_token.get('uid')
    if not firebase_uid:
         raise HTTPException(status_code=401, detail="Invalid token")
         
    result = await db.execute(select(UserModel).where(UserModel.firebase_uid == firebase_uid))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Set tenant context for Row Level Security
    # This ensures all subsequent queries are automatically scoped to this tenant
    current_tenant_id.set(str(user.tenant_id))
        
    # Fetch role slug and display name
    role_slug = None
    role_display_name = None
    if user.role_id:
        from app.rbac_models import Role
        role_result = await db.execute(select(Role).where(Role.id == user.role_id))
        role_obj = role_result.scalar_one_or_none()
        if role_obj:
            role_slug = role_obj.name
            role_display_name = role_obj.display_name

    return {
        "id": user.id,
        "email": user.email,
        "firebase_uid": user.firebase_uid,
        "tenant_id": user.tenant_id,
        "role_id": user.role_id,
        "role": role_slug,
        "role_display_name": role_display_name
    }
