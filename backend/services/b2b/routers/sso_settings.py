"""
SSO Settings Router

API endpoints for tenant owners to view and manage their SSO configuration.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from core.database import get_db
from core.middleware import get_current_user
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
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current SSO configuration for the tenant.
    
    Returns masked client_id for security. Only OWNER/ADMIN can view.
    """
    tenant_id = current_user.get("tenant_id")
    role = current_user.get("role")
    
    # Require OWNER or ADMIN role
    if role not in [B2BRoleName.OWNER, B2BRoleName.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenant owners and admins can view SSO configuration"
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
    
    return SSOConfigResponse(
        provider_type=provider.provider_type,
        provider_id=provider.provider_id,
        client_id=client_id,
        client_id_masked=mask_client_id(client_id),
        issuer=config.get('issuer', ''),
        is_active=provider.is_active,
        has_mobile=False  # TODO: Implement mobile provider detection
    )


@router.put("/sso", response_model=SSOConfigUpdateResponse)
async def update_sso_config(
    request: SSOConfigUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update SSO configuration credentials.
    
    Only OWNER/ADMIN can modify. Updates both Firebase and database.
    """
    tenant_id = current_user.get("tenant_id")
    role = current_user.get("role")
    
    # Require OWNER or ADMIN role
    if role not in [B2BRoleName.OWNER, B2BRoleName.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenant owners and admins can modify SSO configuration"
        )
    
    try:
        await auth_provider_service.update_provider_credentials(
            db=db,
            tenant_id=tenant_id,
            client_id=request.client_id,
            client_secret=request.client_secret,
            issuer=request.issuer
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
