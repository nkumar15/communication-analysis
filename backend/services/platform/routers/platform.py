"""
SaaS Platform Admin API Router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from core.database import get_db
from core.config import settings
from core.utils import get_utc_now
from services.platform.middleware.platform_auth import verify_platform_admin
from services.platform.models import PlatformTenant, PlatformUser
from services.b2b.models import TenantModel, UserModel
from services.b2b.services.tenant_service import tenant_service

router = APIRouter(
    prefix="/api/platform",
    tags=["platform"]
    # NOTE: Auth dependency removed from router level - applied per-route instead
)

# --- Schemas ---

class TenantListResponse(BaseModel):
    id: UUID
    name: str
    domain: str
    status: str
    created_at: datetime
    user_count: int

class TenantCreateRequest(BaseModel):
    name: str
    domain: str
    admin_email: str
    plan: Optional[str] = "free"

class PlatformStats(BaseModel):
    total_tenants: int
    active_tenants: int
    total_users: int

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
    from services.platform.models import PlatformTenant
    
    # Find the singleton platform tenant
    result = await db.execute(select(PlatformTenant))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform configuration not found. Please run seed script."
        )
        
    # Fetch primary auth provider
    from services.platform.models.auth_provider import PlatformAuthProvider
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


@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """Get global platform statistics"""
    
    # Total Tenants
    total_tenants = await db.scalar(
        select(func.count(TenantModel.id)).where(TenantModel.deleted_at.is_(None))
    )
    
    # Active Tenants
    active_tenants = await db.scalar(
        select(func.count(TenantModel.id))
        .where(TenantModel.activation_status == 'active')
        .where(TenantModel.deleted_at.is_(None))
    )
    
    # Total Users
    total_users = await db.scalar(
        select(func.count(UserModel.id)).where(UserModel.deleted_at.is_(None))
    )
    
    return PlatformStats(
        total_tenants=total_tenants or 0,
        active_tenants=active_tenants or 0,
        total_users=total_users or 0
    )

@router.get("/tenants", response_model=List[TenantListResponse])
async def list_tenants(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """List all tenants with basic stats"""
    query = select(TenantModel).where(TenantModel.deleted_at.is_(None))
    
    if search:
        query = query.where(
            (TenantModel.name.ilike(f"%{search}%")) | 
            (TenantModel.domain.ilike(f"%{search}%"))
        )
        
    query = query.offset(skip).limit(limit).order_by(TenantModel.created_at.desc())
    
    result = await db.execute(query)
    tenants = result.scalars().all()
    
    response = []
    for tenant in tenants:
        # Count users for this tenant
        user_count = await db.scalar(
            select(func.count(UserModel.id)).where(UserModel.tenant_id == tenant.id)
        )
        
        response.append(TenantListResponse(
            id=tenant.id,
            name=tenant.name,
            domain=tenant.domain,
            status=tenant.activation_status or 'pending',
            created_at=tenant.created_at,
            user_count=user_count or 0
        ))
        
    return response

@router.post("/tenants")
async def create_tenant(
    request: TenantCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_platform_admin)
):
    """Create a new tenant (Admin only)"""
    # Check domain uniqueness
    existing = await tenant_service.get_tenant_by_domain(db, request.domain)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Domain {request.domain} already exists"
        )
        
    # Create tenant logic
    new_tenant = TenantModel(
        name=request.name,
        domain=request.domain,
        firebase_tenant_id=f"tenant-{request.domain.replace('.', '-')}", # Placeholder
        activation_status='pending'
    )
    
    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)
    
    # Log action
    from services.platform.middleware.platform_auth import log_platform_action
    await log_platform_action(
        admin=current_user,
        action="create_tenant",
        resource_type="tenant",
        resource_id=new_tenant.id,
        details={"domain": request.domain},
        db=db
    )
    
    return {"id": new_tenant.id, "message": "Tenant created successfully"}

@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_platform_admin)
):
    """
    Soft delete a tenant (Admin only)
    
    This will:
    1. Set deleted_at timestamp
    2. Set is_active = False
    3. Log the action
    """
    # Use tenant service to perform soft delete
    success = await tenant_service.delete_tenant(db, tenant_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
        
    # Log action
    from services.platform.middleware.platform_auth import log_platform_action
    await log_platform_action(
        admin=current_user,
        action="delete_tenant",
        resource_type="tenant",
        resource_id=tenant_id,
        details={"soft_delete": True},
        db=db
    )
    
    return {"message": "Tenant deleted successfully"}

class ImpersonationResponse(BaseModel):
    token: str
    tenant_id: UUID
    tenant_name: str
    admin_email: str
    redirect_url: str

@router.post("/tenants/{tenant_id}/impersonate", response_model=ImpersonationResponse)
async def impersonate_tenant_admin(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_platform_admin)
):
    """
    Generate impersonation token for a tenant's admin user
    """
    import jwt
    from datetime import timedelta
    from core.config import settings
    from core.constants import RoleName
    from services.b2b.models import Role
    
    # 1. Fetch tenant
    tenant = await tenant_service.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
    
    # 2. Find tenant's admin user
    admin_role_result = await db.execute(
        select(Role)
        .where(Role.tenant_id == tenant_id)
        .where(Role.name == RoleName.ADMIN)
    )
    admin_role = admin_role_result.scalar_one_or_none()
    
    if not admin_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin role not found for tenant {tenant_id}"
        )
    
    # Find a user with admin role
    admin_user_result = await db.execute(
        select(UserModel)
        .where(UserModel.tenant_id == tenant_id)
        .where(UserModel.role_id == admin_role.id)
        .where(UserModel.is_active == True)
        .limit(1)
    )
    admin_user = admin_user_result.scalar_one_or_none()
    
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active admin user found for tenant {tenant_id}"
        )
    
    # 3. Generate short-lived impersonation token (15 minutes)
    expiry = get_utc_now() + timedelta(minutes=15)
    
    payload = {
        "uid": admin_user.firebase_uid,
        "email": admin_user.email,
        "tenant_id": str(tenant_id),
        "impersonated_by": current_user.get("uid"),
        "iat": get_utc_now().timestamp(),
        "exp": expiry.timestamp()
    }
    
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    
    # 4. Log impersonation action
    from services.platform.middleware.platform_auth import log_platform_action
    
    await log_platform_action(
        admin=current_user,
        action="impersonate_tenant_admin",
        resource_type="tenant",
        resource_id=tenant_id,
        details={"target_user_email": admin_user.email},
        db=db
    )
    
    return ImpersonationResponse(
        token=token,
        tenant_id=tenant_id,
        tenant_name=tenant.name,
        admin_email=admin_user.email,
        redirect_url="/dashboard"
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
    from services.platform.models import PlatformUser, PlatformRole, PlatformTenant
    
    result = await db.execute(
        select(PlatformUser, PlatformRole, PlatformTenant)
        .join(PlatformRole, PlatformUser.platform_role_id == PlatformRole.id)
        .join(PlatformTenant, PlatformUser.platform_tenant_id == PlatformTenant.id)
        .where(PlatformUser.id == current_user["id"])
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Platform admin user not found")
        
    user, role, tenant = row
    
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.display_name,
        "role": role.name,
        "role_display_name": role.display_name,
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name
    }
