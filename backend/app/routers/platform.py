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

from app.database import get_db
from app.middleware.platform_auth import verify_platform_admin
from app.db_models import TenantModel, UserModel
from app.services.tenant_service import tenant_service

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
    from app.db_models import TenantModel
    
    # Find the system tenant via is_system_tenant flag
    query = (
        select(TenantModel)
        .where(TenantModel.is_system_tenant == True)
        .limit(1)
    )
    
    result = await db.execute(query)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System tenant configuration not found"
        )
        
    return PlatformConfigResponse(
        firebase_tenant_id=tenant.firebase_tenant_id,
        oidc_provider_id=tenant.oidc_provider_id or 'oidc.generic',
        tenant_name=tenant.name
    )


@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """Get global platform statistics"""
    
    # Total Tenants
    total_tenants = await db.scalar(select(func.count(TenantModel.id)))
    
    # Active Tenants
    active_tenants = await db.scalar(
        select(func.count(TenantModel.id)).where(TenantModel.activation_status == 'active')
    )
    
    # Total Users
    total_users = await db.scalar(select(func.count(UserModel.id)))
    
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
    query = select(TenantModel)
    
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
    _: dict = Depends(verify_platform_admin)
):
    """Create a new tenant (Admin only)"""
    # Check domain uniqueness
    existing = await tenant_service.get_tenant_by_domain(db, request.domain)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Domain {request.domain} already exists"
        )
        
    # Create tenant logic (simplified for MVP)
    # In real implementation, this would call the full provisioning service
    # For now, we'll just create the tenant record
    
    new_tenant = TenantModel(
        name=request.name,
        domain=request.domain,
        firebase_tenant_id=f"tenant-{request.domain.replace('.', '-')}", # Placeholder
        oidc_provider_id=f"oidc-{request.domain.replace('.', '-')}",     # Placeholder
        activation_status='pending'
    )
    
    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)
    
    return {"id": new_tenant.id, "message": "Tenant created successfully"}

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
    
    This allows platform admins to "Login As" a tenant admin for support purposes.
    """
    import jwt
    from datetime import timedelta
    from app.config import settings
    from app.constants import RoleName
    from app.rbac_models import Role
    
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
    expiry = datetime.utcnow() + timedelta(minutes=15)
    
    payload = {
        "uid": admin_user.firebase_uid,
        "email": admin_user.email,
        "tenant_id": str(tenant_id),
        "impersonated_by": current_user.get("uid"),
        "iat": datetime.utcnow().timestamp(),
        "exp": expiry.timestamp()
    }
    
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    
    # 4. TODO: Log impersonation action for audit trail
    
    return ImpersonationResponse(
        token=token,
        tenant_id=tenant_id,
        tenant_name=tenant.name,
        admin_email=admin_user.email,
        redirect_url="/dashboard"
    )

from app.middleware.auth import get_current_user as base_get_current_user

@router.get("/auth/me")
async def get_platform_admin_info(
    decoded_token: dict = Depends(base_get_current_user),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_platform_admin)
):
    """
    Get platform admin user info
    
    Separate endpoint for platform admins to avoid mixing with tenant user logic
    """
    from app.services.firebase_auth import firebase_auth_service
    from app.db_models import UserModel
    from app.rbac_models import Role
    
    # Extract user info
    user_info = firebase_auth_service.get_user_info(decoded_token)
    firebase_uid = user_info.get("firebase_uid")
    email = user_info.get("email")
    firebase_tenant_id = user_info.get("firebase_tenant_id")
    
    # Get System Tenant by firebase_tenant_id from the token
    # This ensures we get the exact tenant the user authenticated with
    result = await db.execute(
        select(TenantModel).where(TenantModel.firebase_tenant_id == firebase_tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant or not tenant.is_system_tenant:
        raise HTTPException(status_code=404, detail="System tenant not found")
    
    # Find user by email (platform admins are looked up by email, not UID)
    result = await db.execute(
        select(UserModel)
        .where(UserModel.tenant_id == tenant.id)
        .where(UserModel.email == email.lower())
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Platform admin user not found")
    
    # Update Firebase UID if it's different (handles temporary -> real UID transition)
    if user.firebase_uid != firebase_uid:
        user.firebase_uid = firebase_uid
        await db.commit()
        await db.refresh(user)
    
    # Get role info
    result = await db.execute(
        select(Role).where(Role.id == user.role_id)
    )
    role = result.scalar_one_or_none()
    
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": role.name if role else None,
        "role_display_name": role.display_name if role else None,
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name
    }
