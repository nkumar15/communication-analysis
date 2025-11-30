from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from services.b2b.schemas import TenantResolutionRequest, TenantResolutionResponse, UserResponse
from services.b2b.services.tenant_service import tenant_service
from services.b2b.services.user_service import user_service
from services.b2b.services.auth_provider_service import auth_provider_service
from core.utils.firebase import firebase_auth_service
from services.b2b.models import InvitationModel
from core.middleware import get_current_user
from core.database import get_db
from core.constants import B2BRoleName


router = APIRouter(prefix="/api/b2b/auth", tags=["authentication"])


@router.post("/resolve-tenant", response_model=TenantResolutionResponse)
async def resolve_tenant(request: TenantResolutionRequest, db: AsyncSession = Depends(get_db)):
    """
    Resolve tenant from email address
    
    This endpoint extracts the domain from the email and looks up
    the corresponding tenant, returning the Firebase tenant ID that
    the frontend needs to set the auth context.
    """
    # Extract domain from email
    domain = tenant_service.extract_domain_from_email(request.email)
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address"
        )
    
    # Look up tenant by domain
    tenant = await tenant_service.get_tenant_by_domain(db, domain)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tenant found for domain: {domain}"
        )
    
    # Get primary auth provider
    primary_provider = await auth_provider_service.get_primary_provider(db, tenant.id)
    
    return TenantResolutionResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        domain=tenant.domain,
        firebase_tenant_id=tenant.firebase_tenant_id,
        primary_provider_id=primary_provider.provider_id if primary_provider else None
    )






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
    
    # Get tenant from Firebase tenant ID
    tenant = await tenant_service.get_tenant_by_firebase_id(db, firebase_tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found for Firebase tenant: {firebase_tenant_id}"
        )
    
    
    # Check if user already exists by Firebase UID OR by email
    existing_user = await user_service.get_user_by_firebase_uid(db, tenant.id, firebase_uid)
    
    # If not found by UID, check by email (for users created with temporary UIDs)
    if not existing_user:
        from services.b2b.models import UserModel
        result = await db.execute(
            select(UserModel)
            .where(UserModel.tenant_id == tenant.id)
            .where(UserModel.email == email.lower())
            .where(UserModel.is_active == True)
        )
        existing_user_by_email = result.scalar_one_or_none()
        
        if existing_user_by_email:
            # Update Firebase UID if it's a temporary one (starts with "oidc-")
            if existing_user_by_email.firebase_uid.startswith('oidc-'):
                existing_user_by_email.firebase_uid = firebase_uid
                await db.commit()
                await db.refresh(existing_user_by_email)
            existing_user = await user_service._model_to_pydantic(existing_user_by_email, db)
    
    if existing_user:
        # User exists, use default role (it won't overwrite existing role_id)
        user_role = B2BRoleName.VIEWER
    else:
        # New user, check invitation (including accepted ones for initial role assignment)
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.tenant_id == tenant.id)
            .where(InvitationModel.email == email.lower())
        )
        invitation = result.scalar_one_or_none()
        
        # Use role from invitation if exists, otherwise default to 'viewer'
        user_role = invitation.role if invitation else B2BRoleName.VIEWER
    
    # Create or update user
    user = await user_service.create_or_update_user(
        db=db,
        tenant_id=tenant.id,
        email=email,
        firebase_uid=firebase_uid,
        name=name,
        role=user_role  # Use determined role
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,  # Slug (e.g., 'admin')
        role_display_name=user.role_display_name,
        tenant_id=tenant.id,
        tenant_name=tenant.name
    )


@router.post("/sync-user")
async def sync_user(
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
    
    # Get tenant from Firebase tenant ID
    tenant = await tenant_service.get_tenant_by_firebase_id(db, firebase_tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found for Firebase tenant: {firebase_tenant_id}"
        )
    
    # Check if user already exists to preserve their role
    existing_user = await user_service.get_user_by_firebase_uid(db, tenant.id, firebase_uid)
    
    if existing_user:
        # User exists, use default role (it won't overwrite existing role_id)
        user_role = B2BRoleName.VIEWER
    else:
        # New user, check invitation (including accepted ones for initial role assignment)
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.tenant_id == tenant.id)
            .where(InvitationModel.email == email.lower())
        )
        invitation = result.scalar_one_or_none()
        
        # Use role from invitation if exists, otherwise default to 'viewer'
        user_role = invitation.role if invitation else B2BRoleName.VIEWER   
    
    # Create or update user
    user = await user_service.create_or_update_user(
        db=db,
        tenant_id=tenant.id,
        email=email,
        firebase_uid=firebase_uid,
        name=name,
        role=user_role  # Use determined role
    )
    
    return {
        "message": "User synced successfully",
        "user_id": user.id,
        "email": user.email,
        "role": user.role,  # Slug
        "role_display_name": user.role_display_name
    }
