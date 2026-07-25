"""
E2E Tests for Impersonation Feature
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from core.constants import B2BRoleName
from modules.b2b.models.rbac import Role
from modules.b2b.models import TenantModel, UserModel
from tests.conftest import create_test_tenant, create_mock_firebase_token, encode_mock_jwt
# Import platform_admin_setup from existing test file


@pytest_asyncio.fixture
async def tenant_with_admin(db_session: AsyncSession):
    """Create a regular tenant with an admin user"""
    
    # Create tenant
    tenant = await create_test_tenant(
        db_session,
        name="Test Tenant",
        domain=f"test-{uuid4().hex[:6]}.com"
    )
    
    # Find the admin role (created by seed process for each tenant)
    result = await db_session.execute(
        select(Role)
        .where(Role.tenant_id == tenant.id)
        .where(Role.name == B2BRoleName.ADMIN)
    )
    admin_role = result.scalars().first()
    
    # Create admin user directly
    admin_user = UserModel(
        tenant_id=tenant.id,
        email="admin@test.com",
        firebase_uid=f"firebase-admin-{uuid4().hex}",
        name="Test Admin",
        role_id=admin_role.id if admin_role else None,
        is_active=True
    )
    db_session.add(admin_user)
    await db_session.flush()
    await db_session.refresh(admin_user)
    
    return {"tenant": tenant, "admin": admin_user}

@pytest.mark.asyncio
async def test_impersonate_success(api_client: AsyncClient, platform_admin_setup, tenant_with_admin):
    """Platform admin can successfully impersonate tenant admin"""
    platform_token = platform_admin_setup["token"]
    tenant_id = tenant_with_admin["tenant"].id
    
    response = await api_client.post(
        f"/api/platform/b2b/tenants/{tenant_id}/impersonate",
        headers={"Authorization": f"Bearer {platform_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "token" in data
    assert "tenant_id" in data
    assert "tenant_name" in data
    assert "admin_email" in data
    assert "redirect_url" in data
    
    # Verify correct admin email
    assert data["admin_email"] == "admin@test.com"
    assert str(tenant_id) == data["tenant_id"]

@pytest.mark.asyncio
async def test_impersonate_forbidden_regular_user(api_client: AsyncClient, tenant_with_admin):
    """Regular users cannot impersonate"""
    tenant_id = tenant_with_admin["tenant"].id
    
    # Create token for a regular user
    regular_token = encode_mock_jwt(create_mock_firebase_token(
        uid="regular-user",
        email="user@test.com"
    ))
    
    response = await api_client.post(
        f"/api/platform/b2b/tenants/{tenant_id}/impersonate",
        headers={"Authorization": f"Bearer {regular_token}"}
    )
    
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_impersonate_tenant_not_found(api_client: AsyncClient, platform_admin_setup):
    """Returns 404 for non-existent tenant"""
    platform_token = platform_admin_setup["token"]
    fake_tenant_id = uuid4()
    
    response = await api_client.post(
        f"/api/platform/b2b/tenants/{fake_tenant_id}/impersonate",
        headers={"Authorization": f"Bearer {platform_token}"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
