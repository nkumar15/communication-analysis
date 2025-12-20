"""
Account Settings Router
Manage tenant account settings (name, logo, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.b2b.middleware import get_current_active_user
from services.b2b.models import TenantModel
from services.b2b.schemas.account import AccountSettingsResponse, AccountSettingsUpdate
from services.b2b.rbac import has_permission
from core.constants import B2BRoleName


router = APIRouter(prefix="/api/b2b/account", tags=["account"])


@router.get("", response_model=AccountSettingsResponse)
async def get_account_settings(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current tenant account settings
    
    - Requires account:read permission (Admin/Owner)
    - Returns tenant name, domain (read-only), logo, and creation date
    """
    # Check permission
    if not await has_permission(current_user['id'], 'account', 'read', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view account settings"
        )
    # Get tenant
    tenant = await db.get(TenantModel, current_user['tenant_id'])
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return AccountSettingsResponse(
        name=tenant.name,
        domain=tenant.domain,
        logo_url=tenant.logo_url,
        created_at=tenant.created_at
    )


@router.put("", response_model=AccountSettingsResponse)
async def update_account_settings(
    updates: AccountSettingsUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update tenant account settings
    
    - Requires account:write permission (Owner/Admin only)
    - Can update: name, logo_url
    - Domain is read-only and cannot be changed
    """
    # Check permission
    if not await has_permission(current_user['id'], 'account', 'write', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update account settings"
        )
    
    # Get tenant
    tenant = await db.get(TenantModel, current_user['tenant_id'])
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Update fields
    if updates.name is not None:
        if not updates.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name cannot be empty"
            )
        tenant.name = updates.name.strip()
    
    if updates.logo_url is not None:
        tenant.logo_url = updates.logo_url.strip()
    
    # FastAPI's dependency injection for AsyncSession handles commit/rollback automatically
    # No explicit flush or re-query is needed here unless specific RLS context or
    # database-generated values are required immediately before the transaction ends.
    
    return AccountSettingsResponse(
        name=tenant.name,
        domain=tenant.domain,
        logo_url=tenant.logo_url,
        created_at=tenant.created_at
    )
