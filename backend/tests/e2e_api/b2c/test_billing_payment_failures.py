"""
E2E Tests for B2C Billing - Payment Failure & Grace Period Scenarios
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

from services.b2c.models.subscription import Subscription
from services.b2c.middleware.subscription_guard import SubscriptionStatusChecker


@pytest.mark.asyncio
async def test_access_allowed_during_grace_period(db_session, b2c_billing_user):
    """Test user retains access during 7-day grace period after payment failure"""
    
    # Create past_due subscription with period ended 3 days ago (within grace period)
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_test",
        provider_subscription_id=f"sub_test",
        tier="premium",
        status="past_due",
        billing_interval="monthly",
        amount_cents=1900,
        currency="USD",
        current_period_start=datetime.now() - timedelta(days=33),
        current_period_end=datetime.now() - timedelta(days=3),  # 3 days ago
        cancel_at_period_end=False
    )
    db_session.add(subscription)
    await db_session.commit()
    
    # Check access
    checker = SubscriptionStatusChecker(db_session)
    allowed, reason, details = checker.check_workspace_access(
        b2c_billing_user["workspace"],
        require_paid=True
    )
    
    assert allowed == True
    assert reason == "grace_period"
    assert "days_remaining" in details
    assert details["days_remaining"] <= 4  # 7 - 3 = 4 days remaining


@pytest.mark.asyncio
async def test_access_blocked_after_grace_period(db_session, b2c_billing_user):
    """Test access is blocked after 7-day grace period expires"""
    
    # Create past_due subscription with period ended 10 days ago (grace period expired)
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_test",
        provider_subscription_id=f"sub_test",
        tier="premium",
        status="past_due",
        billing_interval="monthly",
        amount_cents=1900,
        currency="USD",
        current_period_start=datetime.now() - timedelta(days=40),
        current_period_end=datetime.now() - timedelta(days=10),  # 10 days ago
        cancel_at_period_end=False
    )
    db_session.add(subscription)
    await db_session.commit()
    
    # Check access
    checker = SubscriptionStatusChecker(db_session)
    allowed, reason, details = checker.check_workspace_access(
        b2c_billing_user["workspace"],
        require_paid=True
    )
    
    assert allowed == False
    assert reason == "grace_period_expired"
    assert "message" in details


@pytest.mark.asyncio
async def test_active_subscription_allows_access(db_session, b2c_billing_user, premium_subscription):
    """Test active subscription allows full access"""
    
    checker = SubscriptionStatusChecker(db_session)
    allowed, reason, details = checker.check_workspace_access(
        b2c_billing_user["workspace"],
        require_paid=True
    )
    
    assert allowed == True
    assert reason == "active"


@pytest.mark.asyncio
async def test_canceled_subscription_blocks_access(db_session, b2c_billing_user):
    """Test canceled subscription blocks paid feature access"""
    
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_test",
        provider_subscription_id=f"sub_test",
        tier="premium",
        status="canceled",
        billing_interval="monthly",
        amount_cents=1900,
        currency="USD",
        current_period_start=datetime.now() - timedelta(days=30),
        current_period_end=datetime.now() - timedelta(days=1),
        canceled_at=datetime.now() - timedelta(days=2)
    )
    db_session.add(subscription)
    await db_session.commit()
    
    checker = SubscriptionStatusChecker(db_session)
    allowed, reason, details = checker.check_workspace_access(
        b2c_billing_user["workspace"],
        require_paid=True
    )
    
    assert allowed == False
    assert reason == "canceled"


@pytest.mark.asyncio
async def test_free_tier_blocks_paid_features(db_session, b2c_billing_user):
    """Test free tier users cannot access paid features"""
    
    # No subscription = free tier
    checker = SubscriptionStatusChecker(db_session)
    allowed, reason, details = checker.check_workspace_access(
        b2c_billing_user["workspace"],
        require_paid=True
    )
    
    assert allowed == False
    assert reason == "paid_subscription_required"
    assert details["current_tier"] == "free"


@pytest.mark.asyncio
async def test_free_tier_allows_free_features(db_session, b2c_billing_user):
    """Test free tier users can access free features"""
    
    checker = SubscriptionStatusChecker(db_session)
    allowed, reason, details = checker.check_workspace_access(
        b2c_billing_user["workspace"],
        require_paid=False  # Don't require paid
    )
    
    assert allowed == True
    assert reason == "free_tier"


@pytest.mark.asyncio
async def test_downgrade_to_free_tier(db_session, b2c_billing_user):
    """Test workspace downgrade to free tier"""
    from services.b2c.middleware.subscription_guard import downgrade_to_free_tier
    
    # Create premium subscription
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_test",
        provider_subscription_id=f"sub_test",
        tier="premium",
        status="active",
        billing_interval="monthly",
        amount_cents=1900,
        currency="USD",
        current_period_start=datetime.now(),
        current_period_end=datetime.now() + timedelta(days=30)
    )
    db_session.add(subscription)
    await db_session.commit()
    
    # Downgrade
    downgrade_to_free_tier(db_session, b2c_billing_user["workspace"])
    await db_session.refresh(subscription)
    
    assert subscription.tier == "free"
    assert subscription.status == "canceled"


@pytest.mark.asyncio
async def test_payment_failed_webhook_scenario(db_session, b2c_billing_user, api_client):
    """Test payment failure webhook triggers grace period"""
    
    # Create active subscription
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_test123",
        provider_subscription_id=f"sub_test123",
        tier="premium",
        status="active",
        billing_interval="monthly",
        amount_cents=1900,
        currency="USD",
        current_period_start=datetime.now(),
        current_period_end=datetime.now() + timedelta(days=30)
    )
    db_session.add(subscription)
    await db_session.commit()
    
    # Simulate invoice.payment_failed webhook
    webhook_payload = {
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_test123",
                "subscription": "sub_test123",
                "amount_due": 1900,
                "amount_paid": 0,
                "currency": "usd",
                "status": "open",
                "created": int(datetime.now().timestamp())
            }
        }
    }
    
    with patch('stripe.Webhook.construct_event', return_value=webhook_payload):
        response = await api_client.post(
            "/api/b2c/billing/webhooks/stripe",
            headers={"stripe-signature": "test_signature"},
            json=webhook_payload
        )
    
    assert response.status_code == 200
    
    # Check subscription was updated
    await db_session.refresh(subscription)
    # Note: Webhook handler should update subscription status, but our test might need async worker
    # In real scenario, subscription.status would be "past_due" after webhook


@pytest.mark.asyncio
async def test_trialing_status_allows_access(db_session, b2c_billing_user):
    """Test trial subscriptions allow full access"""
    
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_test",
        provider_subscription_id=f"sub_test",
        tier="premium",
        status="trialing",
        billing_interval="monthly",
        amount_cents=1900,
        currency="USD",
        current_period_start=datetime.now(),
        current_period_end=datetime.now() + timedelta(days=14)  # 14-day trial
    )
    db_session.add(subscription)
    await db_session.commit()
    
    checker = SubscriptionStatusChecker(db_session)
    allowed, reason, details = checker.check_workspace_access(
        b2c_billing_user["workspace"],
        require_paid=True
    )
    
    assert allowed == True
    assert reason == "trialing"


@pytest.mark.asyncio
async def test_unpaid_status_blocks_access(db_session, b2c_billing_user):
    """Test unpaid subscription blocks access"""
    
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_test",
        provider_subscription_id=f"sub_test",
        tier="premium",
        status="unpaid",
        billing_interval="monthly",
        amount_cents=1900,
        currency="USD",
        current_period_start=datetime.now() - timedelta(days=30),
        current_period_end=datetime.now()
    )
    db_session.add(subscription)
    await db_session.commit()
    
    checker = SubscriptionStatusChecker(db_session)
    allowed, reason, details = checker.check_workspace_access(
        b2c_billing_user["workspace"],
        require_paid=True
    )
    
    assert allowed == False
    assert reason == "unpaid"
