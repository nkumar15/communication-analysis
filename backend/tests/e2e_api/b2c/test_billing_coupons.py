"""
E2E Tests for B2C Billing - Coupons
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

from services.b2c.models.subscription import CouponRedemption


@pytest.mark.asyncio
async def test_validate_active_coupon(api_client: AsyncClient, b2c_billing_user, active_coupon):
    """Test validating an active coupon"""
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.post(
            "/api/b2c/billing/coupons/validate",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"},
            json={
                "code": active_coupon.code,
                "tier": "premium"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] == True
    assert data["code"] == active_coupon.code
    assert data["discount_type"] == "percent"
    assert data["discount_percent"] == 20


@pytest.mark.asyncio
async def test_validate_expired_coupon(api_client: AsyncClient, b2c_billing_user, expired_coupon):
    """Test validating an expired coupon"""
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.post(
            "/api/b2c/billing/coupons/validate",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"},
            json={"code": expired_coupon.code}
        )
    
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_validate_nonexistent_coupon(api_client: AsyncClient, b2c_billing_user):
    """Test validating a coupon that doesn't exist"""
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.post(
            "/api/b2c/billing/coupons/validate",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"},
            json={"code": "NONEXISTENT"}
        )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_validate_coupon_wrong_tier(api_client: AsyncClient, b2c_billing_user, db_session):
    """Test coupon not applicable to tier"""
    from services.b2c.models.subscription import Coupon
    
    # Create premium-only coupon
    coupon = Coupon(
        code="PREMIUMONLY",
        discount_type="percent",
        discount_percent=15,
        currency="USD",
        is_active=True,
        valid_from=datetime.now(),
        valid_until=datetime.now() + timedelta(days=30),
        applicable_tiers=["premium"],  # Only for premium
        description="Premium only"
    )
    db_session.add(coupon)
    await db_session.commit()
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.post(
            "/api/b2c/billing/coupons/validate",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"},
            json={
                "code": "PREMIUMONLY",
                "tier": "ultimate"  # Try to use for ultimate
            }
        )
    
    assert response.status_code == 400
    assert "not applicable" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_coupon_already_redeemed(api_client: AsyncClient, b2c_billing_user, active_coupon, db_session):
    """Test coupon cannot be redeemed twice by same user"""
    
    # Create redemption record
    redemption = CouponRedemption(
        coupon_id=active_coupon.id,
        user_id=b2c_billing_user["user"].id,
        discount_amount_cents=380,  # 20% of $19
        redeemed_at=datetime.now()
    )
    db_session.add(redemption)
    await db_session.commit()
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.post(
            "/api/b2c/billing/coupons/validate",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"},
            json={"code": active_coupon.code}
        )
    
    assert response.status_code == 400
    assert "already" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_coupon_max_redemptions_reached(api_client: AsyncClient, b2c_billing_user, db_session):
    """Test coupon at max redemptions limit"""
    from services.b2c.models.subscription import Coupon
    
    coupon = Coupon(
        code="MAXED",
        discount_type="percent",
        discount_percent=10,
        currency="USD",
        is_active=True,
        valid_from=datetime.now(),
        valid_until=datetime.now() + timedelta(days=30),
        max_redemptions=5,
        times_redeemed=5,  # Already at max
        description="Maxed out"
    )
    db_session.add(coupon)
    await db_session.commit()
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.post(
            "/api/b2c/billing/coupons/validate",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"},
            json={"code": "MAXED"}
        )
    
    assert response.status_code == 400
    assert "maximum" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_available_coupons(api_client: AsyncClient, b2c_billing_user, active_coupon):
    """Test getting list of available coupons"""
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.get(
            "/api/b2c/billing/coupons/available?tier=premium",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "coupons" in data
    assert len(data["coupons"]) > 0
    assert any(c["code"] == active_coupon.code for c in data["coupons"])


@pytest.mark.asyncio
async def test_get_my_redemptions(api_client: AsyncClient, b2c_billing_user, active_coupon, db_session):
    """Test getting user's coupon redemption history"""
    
    # Create redemption
    redemption = CouponRedemption(
        coupon_id=active_coupon.id,
        user_id=b2c_billing_user["user"].id,
        discount_amount_cents=380,
        redeemed_at=datetime.now()
    )
    db_session.add(redemption)
    await db_session.commit()
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.get(
            "/api/b2c/billing/coupons/my-redemptions",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "redemptions" in data
    assert len(data["redemptions"]) == 1
    assert data["redemptions"][0]["coupon_code"] == active_coupon.code
