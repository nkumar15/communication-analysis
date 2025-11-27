"""
E2E Tests for SaaS Platform Admin API
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.constants import RoleName
from app.rbac_models import Role
from tests.conftest import create_test_tenant, create_test_user, create_mock_firebase_token, encode_mock_jwt

@pytest_asyncio.fixture
async def platform_admin_setup(db_session: AsyncSession):
    """Setup System Tenant, Platform Admin Role, and User"""
    from sqlalchemy import select
    from app.db_models import TenantModel, UserModel
    
    # 1. Check/Create System Tenant
    result = await db_session.execute(
        select(TenantModel).where(TenantModel.firebase_tenant_id == "system-platform")
    )
    system_tenant = result.scalar_one_or_none()
    
    if not system_tenant:
        system_tenant = await create_test_tenant(
            db_session,
            name="System Tenant",
            domain="system.local",
            firebase_tenant_id="system-platform"
        )
    
    # 2. Check/Create Platform Admin Role
    result = await db_session.execute(
        select(Role)
        .where(Role.tenant_id == system_tenant.id)
        .where(Role.name == RoleName.PLATFORM_ADMIN)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        role = Role(
            tenant_id=system_tenant.id,
            name=RoleName.PLATFORM_ADMIN,
            display_name="Platform Admin",
            is_system_role=True
        )
        db_session.add(role)
        await db_session.flush()
    
    # 3. Check/Create Platform Admin User
    result = await db_session.execute(
        select(UserModel).where(UserModel.email == "admin@system.local")
    )
    admin_user = result.scalar_one_or_none()
    
    if not admin_user:
        admin_user = await create_test_user(
            db_session,
            tenant_id=system_tenant.id,
            email="admin@system.local",
            role_slug=RoleName.PLATFORM_ADMIN
        )
    
    return {
        "tenant": system_tenant,
        "user": admin_user,
        "token": encode_mock_jwt(create_mock_firebase_token(
            uid=admin_user.firebase_uid,
            email=admin_user.email
        ))
    }

@pytest.mark.asyncio
async def test_platform_stats_access_denied(api_client: AsyncClient):
    """Verify regular user cannot access platform stats"""
    response = await api_client.get("/api/platform/stats")
    assert response.status_code == 401  # No token

    # Create regular user token
    token = encode_mock_jwt(create_mock_firebase_token(uid="regular-user", email="user@test.com"))
    response = await api_client.get(
        "/api/platform/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403  # Forbidden (user not found or no role)

@pytest.mark.asyncio
async def test_platform_stats_success(api_client: AsyncClient, platform_admin_setup):
    """Verify platform admin can access stats"""
    token = platform_admin_setup["token"]
    
    response = await api_client.get(
        "/api/platform/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_tenants" in data
    assert "active_tenants" in data
    assert "total_users" in data
    assert data["total_tenants"] >= 1  # At least system tenant exists

@pytest.mark.asyncio
async def test_create_tenant_via_platform(api_client: AsyncClient, platform_admin_setup):
    """Verify platform admin can create a new tenant"""
    token = platform_admin_setup["token"]
    
    new_tenant_data = {
        "name": "New Platform Tenant",
        "domain": f"platform-test-{uuid4().hex[:6]}.com",
        "admin_email": "admin@new-platform.com",
        "plan": "enterprise"
    }
    
    response = await api_client.post(
        "/api/platform/tenants",
        json=new_tenant_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["message"] == "Tenant created successfully"

@pytest.mark.asyncio
async def test_list_tenants(api_client: AsyncClient, platform_admin_setup):
    """Verify platform admin can list tenants"""
    token = platform_admin_setup["token"]
    
    response = await api_client.get(
        "/api/platform/tenants",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Verify structure
    tenant = data[0]
    assert "id" in tenant
    assert "name" in tenant
    assert "domain" in tenant
    assert "status" in tenant
    assert "user_count" in tenant
