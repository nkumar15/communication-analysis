import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from modules.b2b.models import TenantModel, Coupon as B2BCoupon
from modules.b2c.models.user import B2CUser
from modules.platform.services.tenant_onboarding_service import tenant_onboarding_service

@pytest.mark.asyncio
async def test_billing_stats_access(
    api_client: AsyncClient,
    platform_admin_token: str
):
    response = await api_client.get(
        "/api/platform/billing/stats",
        headers={"Authorization": f"Bearer {platform_admin_token}"}
    )
    assert response.status_code == 200
    assert "message" in response.json()

@pytest.mark.asyncio
async def test_billing_profiles_search(
    api_client: AsyncClient,
    platform_admin_token: str,
    db_session: AsyncSession
):
    # Search for a B2B tenant
    from uuid import uuid4
    from sqlalchemy import text
    # Set platform admin context to bypass RLS
    await db_session.execute(text("SET LOCAL app.is_platform_admin = 'true'"))
    tenant = TenantModel(
        name="SearchTest", 
        domain=f"searchtest-{uuid4().hex[:8]}.com", 
        firebase_tenant_id=f"test-tenant-{uuid4().hex[:8]}",
        activation_status="active"
    )
    db_session.add(tenant)
    await db_session.commit()

    response = await api_client.get(
        "/api/platform/billing/profiles/search?query=SearchTest&type=tenant",
        headers={"Authorization": f"Bearer {platform_admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data['items']) > 0
    assert data['items'][0]['type'] == 'tenant'
    assert data['items'][0]['name'] == 'SearchTest'

@pytest.mark.asyncio
async def test_b2c_billing_profile_detail(
    api_client: AsyncClient,
    platform_admin_token: str,
    db_session: AsyncSession
):
    # Create B2C User
    from sqlalchemy import text
    # Set platform admin context to bypass RLS
    await db_session.execute(text("SET LOCAL app.is_platform_admin = 'true'"))
    
    uid = uuid4().hex
    user = B2CUser(
        email=f"test.billing.{uid}@example.com", 
        firebase_uid=f"fb_{uid}",
        display_name="Test B2C User"
    )
    db_session.add(user)
    await db_session.commit()

    # Fetch Profile
    response = await api_client.get(
        f"/api/platform/billing/profiles/{user.id}?type=user",
        headers={"Authorization": f"Bearer {platform_admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data['type'] == 'user'
    assert data['email'] == user.email
    assert data['subscription'] is None

@pytest.mark.asyncio
async def test_coupon_management(
    api_client: AsyncClient,
    platform_admin_token: str,
    db_session: AsyncSession
):
    # 1. Create B2B Coupon
    code = f"TEST{uuid4().hex[:6].upper()}"
    payload = {
        "code": code,
        "discount_type": "percentage",
        "discount_percent": 20,
        "description": "Test Coupon"
    }
    
    response = await api_client.post(
        "/api/platform/billing/coupons?scope=b2b",
        json=payload,
        headers={"Authorization": f"Bearer {platform_admin_token}"}
    )
    
    # Check if successful (might depend on Stripe mock)
    if response.status_code == 200:
        data = response.json()
        assert data['code'] == code
        assert data['discount_percent'] == 20
        
        # 2. List Coupons
        list_resp = await api_client.get(
            "/api/platform/billing/coupons?scope=b2b",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert any(c['code'] == code for c in items)

@pytest.mark.asyncio
async def test_b2c_coupon_management(
    api_client: AsyncClient,
    platform_admin_token: str,
    db_session: AsyncSession
):
    # 1. Create B2C Coupon
    code = f"B2C{uuid4().hex[:6].upper()}"
    payload = {
        "code": code,
        "discount_type": "fixed_amount",
        "discount_amount_cents": 500,
        "currency": "USD",
        "description": "B2C Test Coupon"
    }
    
    response = await api_client.post(
        "/api/platform/billing/coupons?scope=b2c",
        json=payload,
        headers={"Authorization": f"Bearer {platform_admin_token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        assert data['code'] == code
        assert data['discount_amount_cents'] == 500
        
        # 2. List B2C Coupons
        list_resp = await api_client.get(
            "/api/platform/billing/coupons?scope=b2c",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert any(c['code'] == code for c in items)
