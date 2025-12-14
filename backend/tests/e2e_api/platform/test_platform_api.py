"""
E2E Tests for SaaS Platform Admin API
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from core.constants import PlatformRoleName
from services.b2b.models.rbac import Role
from services.b2b.models import TenantModel, UserModel
from tests.conftest import create_test_tenant, create_test_user, create_mock_firebase_token, encode_mock_jwt



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
    # Handle paginated response structure
    assert "items" in data
    assert "total" in data
    tenants = data["items"]
    assert isinstance(tenants, list)
    assert len(tenants) >= 1
    
    # Verify structure
    tenant = tenants[0]
    assert "id" in tenant
    assert "name" in tenant
    assert "domain" in tenant
    assert "status" in tenant
    assert "user_count" in tenant
