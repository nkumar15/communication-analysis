"""
Activation router for tenant onboarding workflow

Handles activation token validation, SSO testing, and tenant activation.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from uuid import UUID

from modules.b2b.services.tenant_service import tenant_service
from modules.b2b.schemas.activation import (
    ActivationValidationResponse,
    ActivationCompleteRequest,
    ActivationTenantInfoResponse,
    ActivationStatusResponse,
    SSOSetupRequest,
    SSOSetupResponse
)
from core.db.session import get_db
from core.middleware import get_current_user


router = APIRouter(prefix="/api/b2b/activation", tags=["activation"])


@router.get("/validate/{token}", response_model=ActivationValidationResponse)
async def validate_activation_token(token: str, db: AsyncSession = Depends(get_db)):
    """
    Validate activation token and return tenant/invitation info
    
    This is the first step when admin clicks the activation email link.
    Returns tenant details if token is valid and not expired.
    """
    result = await tenant_service.validate_activation_token(db, token)
    return ActivationValidationResponse(**result)


@router.get("/tenant-info/{tenant_id}", response_model=ActivationTenantInfoResponse)
async def get_tenant_for_activation(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get tenant information for SSO configuration
    
    Returns Firebase tenant ID and OIDC provider for frontend to initiate SSO login.
    Called after token validation, before SSO test.
    """
    result = await tenant_service.get_activation_tenant_info(db, tenant_id)
    return ActivationTenantInfoResponse(**result)


@router.post("/complete")
async def complete_activation(
    request: ActivationCompleteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),  # Use base auth, not B2B middleware
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
    
    NOTE: Uses get_current_user (base auth) instead of get_current_active_user (B2B middleware)
    because the tenant is still pending and RLS context needs special handling.
    """
    # Extract Firebase UID from token
    firebase_uid = current_user.get("uid")
    
    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid"
        )
    
    result = await tenant_service.complete_tenant_activation(
        db=db,
        activation_token=request.activation_token,
        firebase_uid=firebase_uid
    )
    
    # Commit transaction
    await db.commit()
    
    return result


@router.get("/check-status/{token}", response_model=ActivationStatusResponse)
async def check_activation_status(token: str, db: AsyncSession = Depends(get_db)):
    """
    Check if activation is complete
    
    Polls this endpoint to detect when user has completed SSO login
    and user record has been created.
    """
    result = await tenant_service.check_activation_status(db, token)
    return ActivationStatusResponse(**result)


@router.post("/setup-sso", response_model=SSOSetupResponse)
async def setup_sso(
    request: SSOSetupRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Configure SSO Provider during activation.
    
    1. Validates activation token.
    2. Calls AuthProviderService to configure GCIP and create DB record.
    """
    from modules.b2b.models import TenantModel
    from modules.b2b.services.auth_provider_service import auth_provider_service
    
    # 1. Validate Token to get Tenant
    validation = await tenant_service.validate_activation_token(db, request.activation_token)
    tenant_id = validation["tenant_id"]
    
    # Get full tenant model for firebase_id
    tenant = await db.get(TenantModel, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    if tenant.activation_status != 'pending':
         raise HTTPException(status_code=400, detail="Tenant is not in pending activation state")

    # 2. Setup Provider
    try:
        provider = await auth_provider_service.setup_initial_provider(
            db=db,
            tenant_id=tenant_id,
            firebase_tenant_id=tenant.firebase_tenant_id,
            provider_type=request.provider_type,
            provider_config=request.provider_config,
            oidc_client_id=request.oidc_client_id,
            oidc_client_secret=request.oidc_client_secret,
            oidc_issuer=request.oidc_issuer,
            saml_entity_id=request.saml_entity_id,
            saml_sso_url=request.saml_sso_url
        )
        
        await db.commit()
        
        return SSOSetupResponse(
            success=True,
            provider_id=provider.provider_id,
            message="SSO configured successfully"
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
