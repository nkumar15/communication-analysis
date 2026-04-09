
import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import create_platform_user, create_platform_tenant, create_mock_firebase_token, encode_mock_jwt

@pytest_asyncio.fixture
async def platform_rbac_setup(db_session: AsyncSession):
    """
    Setup platform users with different roles:
    - Admin
    - Support Staff
    - Billing Manager
    """
    tenant = await create_platform_tenant(db_session)
    
    # Create Admin
    admin_user = await create_platform_user(
        db_session, email=f"admin-{uuid4().hex[:8]}@platform.local", role_name="platform_admin"
    )
    admin_token = encode_mock_jwt(create_mock_firebase_token(admin_user.firebase_uid, admin_user.email, firebase_tenant_id=tenant.firebase_tenant_id))

    # Create Support
    support_user = await create_platform_user(
        db_session, email=f"support-{uuid4().hex[:8]}@platform.local", role_name="support_staff"
    )
    support_token = encode_mock_jwt(create_mock_firebase_token(support_user.firebase_uid, support_user.email, firebase_tenant_id=tenant.firebase_tenant_id))

    # Create Billing
    billing_user = await create_platform_user(
        db_session, email=f"billing-{uuid4().hex[:8]}@platform.local", role_name="billing_manager"
    )
    billing_token = encode_mock_jwt(create_mock_firebase_token(billing_user.firebase_uid, billing_user.email, firebase_tenant_id=tenant.firebase_tenant_id))

    return {
        "tenant": tenant,
        "admin": {"user": admin_user, "token": admin_token},
        "support": {"user": support_user, "token": support_token},
        "billing": {"user": billing_user, "token": billing_token}
    }

@pytest.mark.asyncio
async def test_platform_admin_full_access(api_client: AsyncClient, platform_rbac_setup):
    """Test Platform Admin has full access"""
    setup = platform_rbac_setup
    headers = {"Authorization": f"Bearer {setup['admin']['token']}"}
    
    # 1. List Tenants (Allow)
    resp = await api_client.get("/api/platform/b2b/tenants", headers=headers)
    assert resp.status_code == 200
    
    # 2. Create Tenant (Allow)
    domain = f"admin-test-{uuid4().hex[:8]}.com"
    resp = await api_client.post("/api/platform/b2b/tenants", headers=headers, json={
        "name": "Admin Created",
        "domain": domain,
        "admin_email": "admin@test.com"
    })
    assert resp.status_code == 200
    tenant_id = resp.json()["id"]
    
    # 3. Impersonate (Allow)
    # (Requires a user in the tenant, skipping detailed setup here to keep test focused on Permission Rejection, 
    # but the endpoint check happens before logic execution usually, or we expect 404/400 not 403)
    resp = await api_client.post(f"/api/platform/b2b/tenants/{tenant_id}/impersonate", headers=headers)
    assert resp.status_code != 403 # Might be 404/400 but NOT 403
    
    # 4. Deactivate (Allow)
    resp = await api_client.patch(f"/api/platform/b2b/tenants/{tenant_id}/deactivate", headers=headers)
    assert resp.status_code == 200

    # 5. Delete (Allow)
    resp = await api_client.delete(f"/api/platform/b2b/tenants/{tenant_id}", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_support_staff_access(api_client: AsyncClient, platform_rbac_setup):
    """Test Support Staff access control"""
    setup = platform_rbac_setup
    headers = {"Authorization": f"Bearer {setup['support']['token']}"}
    
    # Create a tenant via Admin first (to act upon)
    domain = f"support-test-{uuid4().hex[:8]}.com"
    resp = await api_client.post("/api/platform/b2b/tenants", 
                               headers={"Authorization": f"Bearer {setup['admin']['token']}"}, 
                               json={"name": "Support Test", "domain": domain, "admin_email": "admin@test.com"})
    tenant_id = resp.json()["id"]

    # 1. List Tenants (Allow)
    resp = await api_client.get("/api/platform/b2b/tenants", headers=headers)
    assert resp.status_code == 200
    
    # 2. Impersonate (Allow)
    resp = await api_client.post(f"/api/platform/b2b/tenants/{tenant_id}/impersonate", headers=headers)
    assert resp.status_code != 403
    
    # 3. Create Tenant (Deny)
    resp = await api_client.post("/api/platform/b2b/tenants", headers=headers, json={
        "name": "Support Created",
        "domain": f"fail-{uuid4().hex[:8]}.com",
        "admin_email": "admin@test.com"
    })
    assert resp.status_code == 403
    
    # 4. Deactivate (Deny)
    resp = await api_client.patch(f"/api/platform/b2b/tenants/{tenant_id}/deactivate", headers=headers)
    assert resp.status_code == 403
    
    # 5. Delete (Deny)
    resp = await api_client.delete(f"/api/platform/b2b/tenants/{tenant_id}", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_billing_manager_access(api_client: AsyncClient, platform_rbac_setup):
    """Test Billing Manager access control"""
    setup = platform_rbac_setup
    headers = {"Authorization": f"Bearer {setup['billing']['token']}"}
    
    # Create a tenant via Admin first
    domain = f"billing-test-{uuid4().hex[:8]}.com"
    resp = await api_client.post("/api/platform/b2b/tenants", 
                               headers={"Authorization": f"Bearer {setup['admin']['token']}"}, 
                               json={"name": "Billing Test", "domain": domain, "admin_email": "admin@test.com"})
    tenant_id = resp.json()["id"]

    # 1. List Tenants (Allow)
    resp = await api_client.get("/api/platform/b2b/tenants", headers=headers)
    assert resp.status_code == 200
    
    # 2. Deactivate (Deny - NO tenants:write permission)
    resp = await api_client.patch(f"/api/platform/b2b/tenants/{tenant_id}/deactivate", headers=headers)
    assert resp.status_code == 403
    
    # 3. Reactivate (Deny - NO tenants:write permission)
    resp = await api_client.patch(f"/api/platform/b2b/tenants/{tenant_id}/reactivate", headers=headers)
    assert resp.status_code == 403
    
    # 4. Create Tenant (Deny)
    resp = await api_client.post("/api/platform/b2b/tenants", headers=headers, json={
        "name": "Billing Created",
        "domain": f"fail-{uuid4().hex[:8]}.com",
        "admin_email": "admin@test.com"
    })
    assert resp.status_code == 403
    
    # 5. Impersonate (Deny)
    resp = await api_client.post(f"/api/platform/b2b/tenants/{tenant_id}/impersonate", headers=headers)
    assert resp.status_code == 403
    
    # 6. Delete (Deny)
    resp = await api_client.delete(f"/api/platform/b2b/tenants/{tenant_id}", headers=headers)
    assert resp.status_code == 403
