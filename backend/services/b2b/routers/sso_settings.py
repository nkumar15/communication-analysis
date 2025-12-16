"""
SSO Settings Router

API endpoints for tenant owners to view and manage their SSO configuration.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from core.database import get_db
from services.b2b.middleware import get_current_active_user
from core.constants import B2BRoleName
from services.b2b.services.auth_provider_service import auth_provider_service
from services.b2b.schemas.sso_settings import (
    SSOConfigResponse,
    SSOConfigUpdateRequest,
    SSOConfigUpdateResponse
)


router = APIRouter(prefix="/api/b2b/settings", tags=["sso-settings"])


def mask_client_id(client_id: str) -> str:
    """Mask client ID for display (show first 3 and last 3 chars)"""
    if len(client_id) <= 6:
        return "***"
    return f"{client_id[:3]}***{client_id[-3:]}"


@router.get("/sso", response_model=SSOConfigResponse)
async def get_sso_config(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current SSO configuration for the tenant.
    
    Returns masked client_id for security. Only OWNER/ADMIN can view.
    """
    tenant_id = current_user.get("tenant_id")
    role = current_user.get("role")
    
    # Debug logging
    print(f"🔍 SSO Config Access - User role: {repr(role)}, Type: {type(role)}")
    print(f"🔍 Checking against: OWNER={repr(B2BRoleName.OWNER)}, ADMIN={repr(B2BRoleName.ADMIN)}")
    
    # Require OWNER or ADMIN role (handle both string and enum)
    allowed_roles = [B2BRoleName.OWNER, B2BRoleName.ADMIN, "owner", "admin"]
    if role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only tenant owners and admins can view SSO configuration. Current role: {role}"
        )
    
    # Get primary auth provider
    provider = await auth_provider_service.get_primary_provider(db, tenant_id)
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No SSO provider configured for this tenant"
        )
    
    # Extract config data
    config = provider.config_data or {}
    client_id = config.get('client_id', '')
    mobile_client_id = config.get('mobile_client_id')
    
    return SSOConfigResponse(
        provider_type=provider.provider_type,
        provider_id=provider.provider_id,
        client_id=client_id,
        client_id_masked=mask_client_id(client_id),
        issuer=config.get('issuer', ''),
        is_active=provider.is_active,
        has_mobile=bool(mobile_client_id),
        mobile_client_id=mobile_client_id,
        mobile_client_id_masked=mask_client_id(mobile_client_id) if mobile_client_id else None
    )


@router.put("/sso", response_model=SSOConfigUpdateResponse)
async def update_sso_config(
    request: SSOConfigUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update SSO configuration credentials.
    
    Only OWNER/ADMIN can modify. Updates both Firebase and database.
    """
    tenant_id = current_user.get("tenant_id")
    role = current_user.get("role")
    
    # Debug logging
    print(f"🔍 SSO Config Update - User role: {repr(role)}, Type: {type(role)}")
    
    # Require OWNER or ADMIN role (handle both string and enum)
    allowed_roles = [B2BRoleName.OWNER, B2BRoleName.ADMIN, "owner", "admin"]
    if role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only tenant owners and admins can modify SSO configuration. Current role: {role}"
        )
    
    try:
        await auth_provider_service.update_provider_credentials(
            db=db,
            tenant_id=tenant_id,
            client_id=request.client_id,
            client_secret=request.client_secret,
            issuer=request.issuer,
            mobile_client_id=request.mobile_client_id,
            mobile_client_secret=request.mobile_client_secret
        )
        
        await db.commit()
        
        # TODO: Log to audit trail
        
        return SSOConfigUpdateResponse(success=True)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
