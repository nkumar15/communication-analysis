"""
SaaS Platform Admin API Router - Core Endpoints
Core platform endpoints that are not product-specific.
B2B and B2C endpoints are in separate routers.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.db.session import get_db
from modules.platform.middleware.platform_auth import verify_platform_admin
from modules.platform.models import PlatformTenant, PlatformUser, PlatformRole

router = APIRouter(
    prefix="/api/platform",
    tags=["platform"]
)

# --- Schemas ---

class PlatformConfigResponse(BaseModel):
    """Public endpoint response for platform login config"""
    firebase_tenant_id: str
    oidc_provider_id: str
    tenant_name: str


# --- Endpoints ---

@router.get("/config", response_model=PlatformConfigResponse)
async def get_platform_config(db: AsyncSession = Depends(get_db)):
    """
    Get system tenant configuration for platform admin login
    
    PUBLIC endpoint (no auth required) - called before login
    """
    # Find the singleton platform tenant
    result = await db.execute(select(PlatformTenant))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform configuration not found. Please run seed script."
        )
        
    # Fetch primary auth provider
    from modules.platform.models.auth_provider import PlatformAuthProvider
    auth_result = await db.execute(
        select(PlatformAuthProvider)
        .where(PlatformAuthProvider.platform_tenant_id == tenant.id)
        .where(PlatformAuthProvider.is_primary == True)
        .where(PlatformAuthProvider.is_active == True)
    )
    auth_provider = auth_result.scalar_one_or_none()
    
    return PlatformConfigResponse(
        firebase_tenant_id=tenant.firebase_tenant_id,
        oidc_provider_id=auth_provider.provider_id if auth_provider else 'oidc.generic',
        tenant_name=tenant.name
    )


@router.get("/auth/me")
async def get_platform_admin_info(
    current_user: dict = Depends(verify_platform_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get platform admin user info
    
    Separate endpoint for platform admins to avoid mixing with tenant user logic
    """
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["display_name"],
        "role": current_user["role"],
        "permissions": current_user.get("permissions", []),
        "tenant_id": current_user["tenant_id"]
    }
