"""
B2B Authentication Router

Handles OAuth flows, mobile login, tenant resolution, and user synchronization.
"""
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks, Request
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from services.b2b.schemas import TenantResolutionRequest, TenantResolutionResponse, UserResponse
from services.b2b.schemas.auth import (
    MobileLoginRequest,
    MobileLoginResponse,
    OIDCConfigResponse
)
from services.b2b.schemas.user import TeamMembership
from services.b2b.services.auth_service import auth_service
from core.utils.firebase import firebase_auth_service
from core.middleware import get_current_user
from core.database import get_db
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/b2b/auth", tags=["authentication"])


@router.post("/mobile-login", response_model=MobileLoginResponse)
async def mobile_login(
    request: MobileLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange OIDC ID token for Firebase ID token using GCIP signInWithIdp
    
    This performs a server-side token exchange with Google Identity Platform.
    It returns a standard Firebase ID Token (not custom token) which ensures
    stable UIDs across Web and Mobile.
    """
    result = await auth_service.mobile_login_exchange(
        db=db,
        oidc_id_token=request.oidc_id_token,
        email=request.email,
        firebase_tenant_id=request.firebase_tenant_id,
        provider_id=request.provider_id,
        nonce=request.nonce
    )
    
    return MobileLoginResponse(**result)


@router.post("/resolve-tenant", response_model=TenantResolutionResponse)
async def resolve_tenant(
    request: TenantResolutionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve tenant from email address
    
    This endpoint extracts the domain from the email and looks up
    the corresponding tenant, returning the Firebase tenant ID that
    the frontend needs to set the auth context.
    """
    result = await auth_service.resolve_tenant_by_email(db, request.email)
    return TenantResolutionResponse(**result)


@router.get("/oidc-config/{provider_id}", response_model=OIDCConfigResponse)
async def get_oidc_config(
    provider_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get OIDC configuration for mobile authentication
    
    Returns the issuer URL, client ID, and scopes needed for
    react-native-app-auth to perform OAuth flow.
    """
    result = await auth_service.get_oidc_config(db, provider_id)
    return OIDCConfigResponse(**result)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    decoded_token: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user
    
    This endpoint validates the Firebase ID token and returns or creates
    the user record in PostgreSQL.
    """
    # Extract user info from token
    user_info = firebase_auth_service.get_user_info(decoded_token)
    
    firebase_uid = user_info.get("firebase_uid")
    email = user_info.get("email")
    name = user_info.get("name")
    firebase_tenant_id = user_info.get("firebase_tenant_id")
    
    if not firebase_uid or not email or not firebase_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing required claims"
        )
    
    # Get or sync user
    user, tenant, permissions, teams = await auth_service.get_or_sync_user(
        db=db,
        firebase_uid=firebase_uid,
        email=email,
        name=name,
        firebase_tenant_id=firebase_tenant_id
    )
    
    # Convert teams to TeamMembership objects
    team_memberships = [
        TeamMembership(id=t["id"], name=t["name"], team_role=t["team_role"])
        for t in teams
    ]
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        role_display_name=user.role_display_name,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        permissions=permissions,
        teams=team_memberships
    )


@router.post("/sync-user")
async def sync_user(
    background_tasks: BackgroundTasks,
    request: Request,
    decoded_token: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync user with database after authentication
    
    This is called by the frontend after successful SSO login
    to ensure user exists in our database.
    """
    # Extract user info from token
    user_info = firebase_auth_service.get_user_info(decoded_token)
    
    firebase_uid = user_info.get("firebase_uid")
    email = user_info.get("email")
    name = user_info.get("name")
    firebase_tenant_id = user_info.get("firebase_tenant_id")
    
    if not firebase_uid or not email or not firebase_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing required claims"
        )
    
    # Get or sync user
    user, tenant, permissions, teams = await auth_service.get_or_sync_user(
        db=db,
        firebase_uid=firebase_uid,
        email=email,
        name=name,
        firebase_tenant_id=firebase_tenant_id
    )
    
    # Capture response data
    res_id = user.id
    res_email = user.email
    res_role = user.role
    res_role_display_name = user.role_display_name
    res_tenant_id = tenant.id
    
    # Commit transaction so background tasks can see the data
    await db.commit()
    
    # Log audit event via Celery (async in production, sync in tests via eager mode)
    from workers.b2b_worker.audit_tasks import persist_audit_log
    persist_audit_log.delay({
        'tenant_id': str(res_tenant_id),
        'event_type': 'auth.login',
        'resource_type': 'user',
        'actor_id': str(res_id),
        'resource_id': str(res_id),
        'details': {'email': email, 'method': 'sso_sync'},
        'ip_address': request.client.host if request.client else None,
        'user_agent': request.headers.get('User-Agent')
    })
    
    return {
        "message": "User synced successfully",
        "user_id": res_id,
        "email": res_email,
        "role": res_role,
        "role_display_name": res_role_display_name,
        "permissions": permissions,
        "teams": teams
    }
