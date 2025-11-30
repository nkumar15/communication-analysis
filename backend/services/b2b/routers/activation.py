"""
Activation router for tenant onboarding workflow
Handles activation token validation, SSO testing, and tenant activation
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID

from services.b2b.services.tenant_service import tenant_service
from services.b2b.services.invitation_service import invitation_service
from services.b2b.services.user_service import user_service
from core.database import get_db
from core.config import settings
from core.middleware import get_current_user


router = APIRouter(prefix="/api/b2b/activation", tags=["activation"])


# Request/Response models

class ActivationValidationResponse(BaseModel):
    """Response for activation token validation"""
    tenant_id: UUID
    tenant_name: str
    domain: str
    admin_email: str
    expires_at: datetime


class ActivationCompleteRequest(BaseModel):
    """Request to complete activation"""
    activation_token: str


# Endpoints

@router.get("/validate/{token}", response_model=ActivationValidationResponse)
async def validate_activation_token(token: str, db: AsyncSession = Depends(get_db)):
    """
    Validate activation token and return tenant/invitation info
    
    This is the first step when admin clicks the activation email link.
    Returns tenant details if token is valid and not expired.
    """
    # Get tenant by activation token
    tenant = await tenant_service.get_tenant_by_activation_token(db, token)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid activation token"
        )
    
    # Check expiry
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    
    if tenant.activation_expires_at and tenant.activation_expires_at < now_utc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Activation token has expired"
        )
    
    # Check not already activated
    if tenant.activation_status == 'active':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant is already activated"
        )
    
    # Get invitation for admin email
    invitation = await invitation_service.get_invitation_by_token(db, token)
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    return ActivationValidationResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        domain=tenant.domain,
        admin_email=invitation.email,
        expires_at=tenant.activation_expires_at
    )


@router.get("/tenant-info/{tenant_id}")
async def get_tenant_for_activation(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get tenant information for SSO configuration
    
    Returns Firebase tenant ID and OIDC provider for frontend to initiate SSO login.
    Called after token validation, before SSO test.
    """
    tenant = await tenant_service.get_tenant_by_id(db, tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Get primary auth provider
    from services.b2b.services.auth_provider_service import auth_provider_service
    primary_provider = await auth_provider_service.get_primary_provider(db, tenant.id)
    
    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "firebase_tenant_id": tenant.firebase_tenant_id,
        "oidc_provider_id": primary_provider.provider_id if primary_provider else None
    }


@router.post("/complete")
async def complete_activation(
    request: ActivationCompleteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Complete tenant activation after successful SSO login
    
    This is called after:
    1. Admin validates token
    2. Admin logs in via SSO (creating user record)
    3. Admin confirms activation
    
    Marks tenant as active and accepts the invitation.
    Prevents replay attacks via activation_started_at check.
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select, update
    from services.b2b.models import TenantModel
    
    # Get tenant with atomic locking
    result = await db.execute(
        select(TenantModel)
        .where(TenantModel.activation_token == request.activation_token)
        .with_for_update()  # Lock row to prevent race conditions
    )
    tenant_model = result.scalar_one_or_none()
    
    if not tenant_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid activation token"
        )
    
    # Check if activation already started (prevents replay attacks)
    if tenant_model.activation_started_at:
        # Allow a grace period of 5 minutes in case of legitimate retries
        grace_period = timedelta(minutes=5)
        time_since_start = datetime.now(timezone.utc) - tenant_model.activation_started_at
        
        if time_since_start > grace_period:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Activation already in progress or completed"
            )
    else:
        # Mark activation as started (prevents concurrent attempts)
        tenant_model.activation_started_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(tenant_model)
    
    # Convert to Pydantic model
    tenant = tenant_service._model_to_pydantic(tenant_model)
    
    # Verify current user belongs to this tenant
    user_info = current_user  # From Firebase token
    firebase_uid = user_info.get("uid")  # Firebase tokens use 'uid' not 'firebase_uid'
    
    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid"
        )
    
    # Get user from database
    user = await user_service.get_user_by_firebase_uid(db, tenant.id, firebase_uid)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found for this tenant"
        )
    
    # Verify user has admin role
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can activate tenants"
        )
    
    # Mark invitation as accepted
    await invitation_service.accept_invitation(db, request.activation_token)
    
    # Activate tenant
    await tenant_service.activate_tenant(db, tenant.id, user.id)
    
    return {
        "message": "Tenant activated successfully",
        "tenant_id": tenant.id,
        "tenant_name": tenant.name
    }


@router.get("/check-status/{token}")
async def check_activation_status(token: str, db: AsyncSession = Depends(get_db)):
    """
    Check if activation is complete
    
    Polls this endpoint to detect when user has completed SSO login
    and user record has been created.
    """
    tenant = await tenant_service.get_tenant_by_activation_token(db, token)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid activation token"
        )
    
    # Check if invitation exists and get admin email
    invitation = await invitation_service.get_invitation_by_token(db, token)
    
    if not invitation:
        return {"status": "invalid", "message": "Invitation not found"}
    
    # Check if user has been created (SSO login completed)
    from sqlalchemy import select
    from services.b2b.models import UserModel
    
    result = await db.execute(
        select(UserModel)
        .where(UserModel.tenant_id == tenant.id)
        .where(UserModel.email == invitation.email)
        .where(UserModel.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if user:
        return {
            "status": "ready",
            "message": "SSO login successful, ready to complete activation",
            "user_created": True
        }
    else:
        return {
            "status": "pending",
            "message": "Waiting for SSO login",
            "user_created": False
        }
