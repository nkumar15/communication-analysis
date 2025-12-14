"""
Platform B2B API Router - Enterprise Tenant Management
All B2B-related endpoints under /api/platform/b2b/*
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from uuid import UUID

from core.database import get_db
from core.config import settings
from services.platform.middleware.platform_auth import verify_platform_admin, log_platform_action
from services.b2b.models import TenantModel, UserModel, AuthProvider, Team, Role
from services.b2b.services.tenant_service import tenant_service
from services.platform.services.tenant_onboarding_service import tenant_onboarding_service
from services.platform.schemas.platform_schemas import (
    TenantOnboardRequest,
    TenantOnboardResponse,
    TenantDetailResponse,
    ResendActivationResponse,
    DeactivateTenantResponse,
    AuthProviderInfo
)

router = APIRouter(
    prefix="/api/platform/b2b",
    tags=["platform-b2b"]
)

# --- Schemas ---

class B2BStats(BaseModel):
    total_tenants: int
    active_tenants: int
    pending_tenants: int
    total_users: int

class TenantItem(BaseModel):
    id: UUID
    name: str
    domain: str
    status: str
    created_at: datetime
    user_count: int

class TenantListResponse(BaseModel):
    items: List[TenantItem]
    total: int
    page: int
    limit: int

class TenantCreateRequest(BaseModel):
    name: str
    domain: str
    admin_email: str
    plan: Optional[str] = "free"

class ImpersonationResponse(BaseModel):
    token: str
    tenant_id: UUID
    tenant_name: str
    admin_email: str
    redirect_url: str


# --- Endpoints ---

@router.get("/stats", response_model=B2BStats)
async def get_b2b_stats(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """Get B2B platform statistics (enterprise tenants)"""
    from core.rls import rls_service
    await rls_service.set_platform_admin_context(db)
    
    total_tenants = await db.scalar(
        select(func.count(TenantModel.id)).where(TenantModel.deleted_at.is_(None))
    )
    
    active_tenants = await db.scalar(
        select(func.count(TenantModel.id))
        .where(TenantModel.activation_status == 'active')
        .where(TenantModel.deleted_at.is_(None))
    )
    
    pending_tenants = await db.scalar(
        select(func.count(TenantModel.id))
        .where(TenantModel.activation_status == 'pending')
        .where(TenantModel.deleted_at.is_(None))
    )
    
    total_users = await db.scalar(
        select(func.count(UserModel.id)).where(UserModel.deleted_at.is_(None))
    )
    
    return B2BStats(
        total_tenants=total_tenants or 0,
        active_tenants=active_tenants or 0,
        pending_tenants=pending_tenants or 0,
        total_users=total_users or 0
    )


@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """List all B2B tenants with basic stats"""
    from core.rls import rls_service
    await rls_service.set_platform_admin_context(db)
    
    query = select(TenantModel).where(TenantModel.deleted_at.is_(None))
    
    if search:
        query = query.where(
            (TenantModel.name.ilike(f"%{search}%")) | 
            (TenantModel.domain.ilike(f"%{search}%"))
        )
    
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    paginated_query = query.offset(skip).limit(limit).order_by(TenantModel.created_at.desc())
    result = await db.execute(paginated_query)
    tenants = result.scalars().all()
    
    items = []
    for tenant in tenants:
        user_count = await db.scalar(
            select(func.count(UserModel.id)).where(UserModel.tenant_id == tenant.id)
        )
        items.append(TenantItem(
            id=tenant.id,
            name=tenant.name,
            domain=tenant.domain,
            status=tenant.activation_status or 'pending',
            created_at=tenant.created_at,
            user_count=user_count or 0
        ))
        
    return TenantListResponse(
        items=items,
        total=total or 0,
        page=(skip // limit) + 1,
        limit=limit
    )


@router.post("/tenants")
async def create_tenant(
    request: TenantCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_platform_admin)
):
    """Create a new B2B tenant"""
    existing = await tenant_service.get_tenant_by_domain(db, request.domain)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Domain {request.domain} already exists"
        )
        
    new_tenant = TenantModel(
        name=request.name,
        domain=request.domain,
        firebase_tenant_id=f"tenant-{request.domain.replace('.', '-')}",
        activation_status='pending'
    )
    
    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)
    
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
    """Soft delete a B2B tenant"""
    success = await tenant_service.delete_tenant(db, tenant_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
        
    await log_platform_action(
        admin=current_user,
        action="delete_tenant",
        resource_type="tenant",
        resource_id=tenant_id,
        details={"soft_delete": True},
        db=db
    )
    
    return {"message": "Tenant deleted successfully"}


@router.post("/tenants/{tenant_id}/impersonate", response_model=ImpersonationResponse)
async def impersonate_tenant_admin(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_platform_admin)
):
    """Generate impersonation token for a tenant's admin user"""
    import jwt
    from core.constants import B2BRoleName
    from core.rls import rls_service
    
    await rls_service.set_platform_admin_context(db)
    
    tenant = await tenant_service.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
    
    roles_result = await db.execute(
        select(Role)
        .where(Role.tenant_id == tenant_id)
        .where(Role.name.in_([B2BRoleName.OWNER, B2BRoleName.ADMIN]))
    )
    roles = roles_result.scalars().all()
    
    owner_role = next((r for r in roles if r.name == B2BRoleName.OWNER), None)
    admin_role = next((r for r in roles if r.name == B2BRoleName.ADMIN), None)
    
    target_user = None
    
    if owner_role:
        user_result = await db.execute(
            select(UserModel)
            .where(UserModel.tenant_id == tenant_id)
            .where(UserModel.role_id == owner_role.id)
            .where(UserModel.is_active == True)
            .limit(1)
        )
        target_user = user_result.scalar_one_or_none()
    
    if not target_user and admin_role:
        user_result = await db.execute(
            select(UserModel)
            .where(UserModel.tenant_id == tenant_id)
            .where(UserModel.role_id == admin_role.id)
            .where(UserModel.is_active == True)
            .limit(1)
        )
        target_user = user_result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active owner or admin user found for tenant {tenant_id}"
        )
    
    payload = {
        "sub": target_user.firebase_uid,
        "email": target_user.email,
        "tenant_id": str(tenant.id),
        "role": B2BRoleName.OWNER if (owner_role and target_user.role_id == owner_role.id) else B2BRoleName.ADMIN,
        "type": "impersonation",
        "impersonator": current_user["email"],
        "exp": datetime.utcnow() + timedelta(minutes=60)
    }
    
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    
    await log_platform_action(
        admin=current_user,
        action="impersonate_tenant_admin",
        resource_type="tenant",
        resource_id=tenant_id,
        details={"target_user_email": target_user.email},
        db=db
    )
    
    return ImpersonationResponse(
        token=token,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        admin_email=target_user.email,
        redirect_url=f"{settings.frontend_url}/auth/impersonate?token={token}"
    )


@router.post("/tenants/onboard", response_model=TenantOnboardResponse, status_code=status.HTTP_201_CREATED)
async def onboard_tenant(
    request: TenantOnboardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_platform_admin)
):
    """Full B2B tenant onboarding workflow"""
    try:
        from core.rls import rls_service
        await rls_service.set_platform_admin_context(db)
        
        result = await tenant_onboarding_service.onboard_tenant(
            db=db,
            company_name=request.company_name,
            domain=request.domain,
            owner_email=request.owner_email,
            provider_type=request.provider_type,
            provider_config=request.provider_config,
            oidc_client_id=request.oidc_client_id,
            oidc_client_secret=request.oidc_client_secret,
            oidc_issuer=request.oidc_issuer
        )
        
        await db.commit()
        
        await log_platform_action(
            admin=current_user,
            action="onboard_tenant",
            resource_type="tenant",
            resource_id=result["tenant_id"],
            details={"domain": request.domain, "company": request.company_name},
            db=db
        )
        
        return TenantOnboardResponse(**result)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tenants/{tenant_id}/details", response_model=TenantDetailResponse)
async def get_tenant_details(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """Get detailed B2B tenant information"""
    from core.rls import rls_service
    await rls_service.set_platform_admin_context(db)
    
    tenant = await db.get(TenantModel, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
    
    user_count = await db.scalar(
        select(func.count(UserModel.id)).where(UserModel.tenant_id == tenant_id)
    )
    
    team_count = await db.scalar(
        select(func.count(Team.id))
        .where(Team.tenant_id == tenant_id)
        .where(Team.deleted_at.is_(None))
    )
    
    auth_result = await db.execute(
        select(AuthProvider)
        .where(AuthProvider.tenant_id == tenant_id)
        .where(AuthProvider.is_primary == True)
    )
    auth_provider = auth_result.scalar_one_or_none()
    
    auth_info = None
    if auth_provider:
        auth_info = AuthProviderInfo(
            provider_type=auth_provider.provider_type,
            provider_id=auth_provider.provider_id,
            display_name=auth_provider.display_name,
            is_primary=auth_provider.is_primary,
            is_active=auth_provider.is_active
        )
    
    return TenantDetailResponse(
        id=tenant.id,
        name=tenant.name,
        domain=tenant.domain,
        firebase_tenant_id=tenant.firebase_tenant_id,
        activation_status=tenant.activation_status or 'pending',
        activation_token=tenant.activation_token if tenant.activation_status == 'pending' else None,
        activation_expires_at=tenant.activation_expires_at,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        user_count=user_count or 0,
        team_count=team_count or 0,
        auth_provider=auth_info
    )


@router.post("/tenants/{tenant_id}/resend-activation", response_model=ResendActivationResponse)
async def resend_activation_email(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_platform_admin)
):
    """Regenerate activation token and resend activation email"""
    try:
        result = await tenant_onboarding_service.resend_activation(db, tenant_id)
        await db.commit()
        
        await log_platform_action(
            admin=current_user,
            action="resend_activation",
            resource_type="tenant",
            resource_id=str(tenant_id),
            details={},
            db=db
        )
        
        return ResendActivationResponse(**result)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/tenants/{tenant_id}/deactivate", response_model=DeactivateTenantResponse)
async def deactivate_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_platform_admin)
):
    """Deactivate a B2B tenant (soft deactivation, preserves data)"""
    tenant = await db.get(TenantModel, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
    
    tenant.is_active = False
    await db.commit()
    
    await log_platform_action(
        admin=current_user,
        action="deactivate_tenant",
        resource_type="tenant",
        resource_id=str(tenant_id),
        details={},
        db=db
    )
    
    return DeactivateTenantResponse(tenant_id=str(tenant_id))
