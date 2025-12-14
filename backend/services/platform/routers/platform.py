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
from services.b2b.models import TenantModel, UserModel, AuthProvider, Team
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
    prefix="/api/platform",
    tags=["platform"]
    # NOTE: Auth dependency removed from router level - applied per-route instead
)

# --- Schemas ---

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
    
    # Explicitly set platform admin context
    from core.rls import rls_service
    await rls_service.set_platform_admin_context(db)
    
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

@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """List all tenants with basic stats"""
    
    # Explicitly set platform admin context
    from core.rls import rls_service
    await rls_service.set_platform_admin_context(db)
    
    # Base query for counting and selecting
    query = select(TenantModel).where(TenantModel.deleted_at.is_(None))
    
    if search:
        query = query.where(
            (TenantModel.name.ilike(f"%{search}%")) | 
            (TenantModel.domain.ilike(f"%{search}%"))
        )
    
    # Get total count for pagination
    # Note: We need to clone the query or construct a count query
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
        
    # Apply pagination
    paginated_query = query.offset(skip).limit(limit).order_by(TenantModel.created_at.desc())
    
    result = await db.execute(paginated_query)
    tenants = result.scalars().all()
    
    items = []
    for tenant in tenants:
        # Count users for this tenant
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
    from core.constants import PlatformRoleName, B2BRoleName
    from services.b2b.models import Role
    
    # 1. Fetch tenant
    # Explicitly set platform admin context to ensure RLS bypass works
    from core.rls import rls_service
    await rls_service.set_platform_admin_context(db)
    
    tenant = await tenant_service.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
     # 2. Find an admin user to impersonate (Owner or Admin)
    # Fetch both roles
    roles_result = await db.execute(
        select(Role)
        .where(Role.tenant_id == tenant_id)
        .where(Role.name.in_([B2BRoleName.OWNER, B2BRoleName.ADMIN]))
    )
    roles = roles_result.scalars().all()
    
    owner_role = next((r for r in roles if r.name == B2BRoleName.OWNER), None)
    admin_role = next((r for r in roles if r.name == B2BRoleName.ADMIN), None)
    
    target_user = None
    
    # Try to find an active Owner user first
    if owner_role:
        user_result = await db.execute(
            select(UserModel)
            .where(UserModel.tenant_id == tenant_id)
            .where(UserModel.role_id == owner_role.id)
            .where(UserModel.is_active == True)
            .limit(1)
        )
        target_user = user_result.scalar_one_or_none()
    
    # Fallback: Try to find an active Admin user if no Owner user found
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
    
    # 3. Generate impersonation token
    # Create a short-lived JWT for the target user
    expiration = timedelta(minutes=60)
    
    # We need to get the user's firebase_uid to create a proper token
    # But since we are impersonating, we might want to create a custom token
    # For now, we'll create a session token that the frontend can use
    
    payload = {
        "sub": target_user.firebase_uid,
        "email": target_user.email,
        "tenant_id": str(tenant.id),
        "role": B2BRoleName.OWNER if (owner_role and target_user.role_id == owner_role.id) else B2BRoleName.ADMIN,
        "type": "impersonation",
        "impersonator": current_user["email"],
        "exp": datetime.utcnow() + expiration
    }
    
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    

    
    # 4. Log impersonation action
    from services.platform.middleware.platform_auth import log_platform_action
    
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


# ============================================================================
# NEW TENANT ONBOARDING ENDPOINTS
# ============================================================================

@router.post("/tenants/onboard", response_model=TenantOnboardResponse, status_code=status.HTTP_201_CREATED)
async def onboard_tenant(
    request: TenantOnboardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_platform_admin)
):
    """
    Full tenant onboarding workflow
    
    Creates Firebase tenant, configures OIDC, seeds roles, creates default team,
    sends activation email. Replaces the CLI tenant_onboard script.
    """
    try:
        # Explicitly set platform admin context to ensure RLS bypass works
        from core.rls import rls_service
        await rls_service.set_platform_admin_context(db)
        
        result = await tenant_onboarding_service.onboard_tenant(
            db=db,
            company_name=request.company_name,
            domain=request.domain,
            owner_email=request.owner_email,
            provider_type=request.provider_type,
            provider_config=request.provider_config,
            # Legacy fields - passed as fallback since we made them optional in schema but logic might want them
            # if provider_config wasn't fully populated by frontend yet.
            # Service normalizes this.
            # oidc_provider removed from signature
            oidc_client_id=request.oidc_client_id,
            oidc_client_secret=request.oidc_client_secret,
            oidc_issuer=request.oidc_issuer
        )
        
        await db.commit()
        
        # Log action
        from services.platform.middleware.platform_auth import log_platform_action
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
    """
    Get detailed tenant information including auth provider and stats
    """
    # Explicitly set platform admin context
    from core.rls import rls_service
    await rls_service.set_platform_admin_context(db)
    
    # Get tenant
    tenant = await db.get(TenantModel, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
    
    # Get user count
    user_count = await db.scalar(
        select(func.count(UserModel.id)).where(UserModel.tenant_id == tenant_id)
    )
    
    # Get team count
    team_count = await db.scalar(
        select(func.count(Team.id))
        .where(Team.tenant_id == tenant_id)
        .where(Team.deleted_at.is_(None))
    )
    
    # Get auth provider
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
    """
    Regenerate activation token and resend activation email
    """
    try:
        result = await tenant_onboarding_service.resend_activation(db, tenant_id)
        await db.commit()
        
        # Log action
        from services.platform.middleware.platform_auth import log_platform_action
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
    """
    Deactivate a tenant (soft deactivation, preserves data)
    
    Different from delete - sets is_active=False but keeps all data
    """
    tenant = await db.get(TenantModel, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
    
    tenant.is_active = False
    await db.commit()
    
    # Log action
    from services.platform.middleware.platform_auth import log_platform_action
    await log_platform_action(
        admin=current_user,
        action="deactivate_tenant",
        resource_type="tenant",
        resource_id=str(tenant_id),
        details={},
        db=db
    )
    
    return DeactivateTenantResponse(tenant_id=str(tenant_id))
