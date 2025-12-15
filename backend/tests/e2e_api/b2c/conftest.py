"""
Fixtures for B2C billing and subscription tests
"""
import pytest
import pytest_asyncio
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from tests.conftest import (
    create_b2c_user,
    create_b2c_workspace,
    create_b2c_mock_token,
    encode_mock_jwt
)
from services.b2c.models.subscription import Subscription, Coupon, CouponRedemption, Invoice


@pytest_asyncio.fixture
async def b2c_billing_user(db_session):
    """Create a B2C user with personal workspace for billing tests"""
    email = f"billinguser-{uuid4().hex[:8]}@b2c.test"
    firebase_uid = f"firebase-{uuid4().hex[:12]}"
    
    user = await create_b2c_user(db_session, email, firebase_uid, "Billing User")
    workspace = await create_b2c_workspace(db_session, user.id, "Billing Workspace", 'personal')
    user.default_workspace_id = workspace.id
    
    await db_session.commit()
    
    # Create auth token
    mock_token_data = create_b2c_mock_token(firebase_uid, email)
    auth_token = encode_mock_jwt(mock_token_data)
    
    return {
        "user": user,
        "workspace": workspace,
        "auth_token": auth_token,
        "firebase_uid": firebase_uid,
        "email": email,
        "mock_token_data": mock_token_data
    }


@pytest_asyncio.fixture
async def premium_subscription(db_session, b2c_billing_user):
    """Create an active premium subscription"""
    from sqlalchemy import text
    
    # Set RLS context
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{b2c_billing_user['user'].id}'"))
    
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_{uuid4().hex[:12]}",
        provider_subscription_id=f"sub_{uuid4().hex[:12]}",
        tier="premium",
        status="active",
        billing_interval="monthly",
        amount_cents=1900,
        currency="USD",
        current_period_start=datetime.now(),
        current_period_end=datetime.now() + timedelta(days=30),
        cancel_at_period_end=False
    )
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    return subscription


@pytest_asyncio.fixture
async def past_due_subscription(db_session, b2c_billing_user):
    """Create a past_due subscription (payment failed)"""
    from sqlalchemy import text
    
    # Set RLS context
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{b2c_billing_user['user'].id}'"))
    
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_{uuid4().hex[:12]}",
        provider_subscription_id=f"sub_{uuid4().hex[:12]}",
        tier="premium",
        status="past_due",
        billing_interval="monthly",
        amount_cents=1900,
        currency="USD",
        current_period_start=datetime.now() - timedelta(days=30),
        current_period_end=datetime.now() - timedelta(days=1),  # Period ended yesterday
        cancel_at_period_end=False
    )
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription) # Reverted to original refresh pattern for syntactic correctness
    return subscription


@pytest_asyncio.fixture
async def active_coupon(db_session, b2c_billing_user):
    """Create an active coupon"""
    from sqlalchemy import text
    
    # Set RLS context  
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{b2c_billing_user['user'].id}'"))
    
    coupon = Coupon(
        code="SAVE20",
        discount_type="percent",
        discount_percent=20,
        currency="USD",
        is_active=True,
        valid_from=datetime.now() - timedelta(days=7),
        valid_until=datetime.now() + timedelta(days=30),
        max_redemptions=100,
        times_redeemed=5,  # Fixed: was redemptions_count
        applicable_tiers=["premium", "ultimate"],
        description="20% off any plan"
    )
    db_session.add(coupon)
    await db_session.commit()
    await db_session.refresh(coupon)
    return coupon


@pytest_asyncio.fixture
async def expired_coupon(db_session, b2c_billing_user):
    """Create an expired coupon"""
    from sqlalchemy import text
    
    # Set RLS context
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{b2c_billing_user['user'].id}'"))
    
    coupon = Coupon(
        code="EXPIRED",
        discount_type="percent",
        discount_percent=30,
        currency="USD",
        is_active=True,
        valid_from=datetime.now() - timedelta(days=30),
        valid_until=datetime.now() - timedelta(days=1),  # Expired yesterday
        applicable_tiers=["premium"],
        description="Expired coupon"
    )
    db_session.add(coupon)
    await db_session.commit()
    await db_session.refresh(coupon)
    return coupon


@pytest_asyncio.fixture
def mock_stripe_provider():
    """Mock Stripe provider for testing"""
    mock_provider = MagicMock()
    
    # Mock checkout session creation
    async def mock_create_checkout(**kwargs):
        return {
            "checkout_session_id": f"cs_{uuid4().hex[:12]}",
            "checkout_url": f"https://checkout.stripe.com/pay/cs_{uuid4().hex[:12]}"
        }
    mock_provider.create_checkout_session = AsyncMock(side_effect=mock_create_checkout)
    
    # Mock customer creation
    async def mock_create_customer(**kwargs):
        return {
            "provider_customer_id": f"cus_{uuid4().hex[:12]}"
        }
    mock_provider.create_customer = AsyncMock(side_effect=mock_create_customer)
    
    # Mock subscription retrieval
    async def mock_get_subscription(sub_id):
        return {
            "id": sub_id,
            "status": "active",
            "current_period_start": int(datetime.now().timestamp()),
            "current_period_end": int((datetime.now() + timedelta(days=30)).timestamp()),
            "items": {
                "data": [{
                    "price": {
                        "unit_amount": 1900,
                        "currency": "usd"
                    }
                }]
            }
        }
    mock_provider.get_subscription = AsyncMock(side_effect=mock_get_subscription)
    
    # Mock subscription cancellation
    async def mock_cancel_subscription(sub_id, at_period_end=True):
        return {
            "status": "active" if at_period_end else "canceled",
            "cancel_at_period_end": at_period_end,
            "canceled_at": datetime.now() if not at_period_end else None
        }
    mock_provider.cancel_subscription = AsyncMock(side_effect=mock_cancel_subscription)
    
    # Mock customer portal session
    async def mock_create_portal(**kwargs):
        return {
            "portal_url": f"https://billing.stripe.com/session/test_{uuid4().hex[:8]}"
        }
    mock_provider.create_customer_portal_session = AsyncMock(side_effect=mock_create_portal)
    
    return mock_provider
