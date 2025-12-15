"""
E2E Tests for B2C Billing - Payment Failure & Grace Period Scenarios

These tests verify subscription status handling for various payment scenarios.
Tests focus on data creation and validation using async fixtures.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta
from uuid import uuid4

from services.b2c.models.subscription import Subscription
from core.rls import rls_service


@pytest.mark.asyncio
async def test_past_due_subscription_created_correctly(db_session, b2c_billing_user):
    """Test that a past_due subscription can be created with correct RLS context"""
    
    await rls_service.set_user_context(db_session, b2c_billing_user['user'].id)
    
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
        current_period_start=datetime.now() - timedelta(days=33),
        current_period_end=datetime.now() - timedelta(days=3),
        cancel_at_period_end=False
    )
    db_session.add(subscription)
    await db_session.flush()
    
    assert subscription.id is not None
    assert subscription.status == "past_due"


@pytest.mark.asyncio
async def test_canceled_subscription_created_correctly(db_session, b2c_billing_user):
    """Test that a canceled subscription can be created with correct RLS context"""
    
    await rls_service.set_user_context(db_session, b2c_billing_user['user'].id)
    
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_{uuid4().hex[:12]}",
        provider_subscription_id=f"sub_{uuid4().hex[:12]}",
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
    await db_session.flush()
    
    assert subscription.id is not None
    assert subscription.status == "canceled"
    assert subscription.canceled_at is not None


@pytest.mark.asyncio
async def test_trialing_subscription_created_correctly(db_session, b2c_billing_user):
    """Test that a trialing subscription can be created with correct RLS context"""
    
    await rls_service.set_user_context(db_session, b2c_billing_user['user'].id)
    
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_{uuid4().hex[:12]}",
        provider_subscription_id=f"sub_{uuid4().hex[:12]}",
        tier="premium",
        status="trialing",
        billing_interval="monthly",
        amount_cents=1900,
        currency="USD",
        current_period_start=datetime.now(),
        current_period_end=datetime.now() + timedelta(days=14)
    )
    db_session.add(subscription)
    await db_session.flush()
    
    assert subscription.id is not None
    assert subscription.status == "trialing"


@pytest.mark.asyncio
async def test_incomplete_subscription_created_correctly(db_session, b2c_billing_user):
    """Test that an incomplete subscription can be created with correct RLS context"""
    
    await rls_service.set_user_context(db_session, b2c_billing_user['user'].id)
    
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_{uuid4().hex[:12]}",
        provider_subscription_id=f"sub_{uuid4().hex[:12]}",
        tier="premium",
        status="incomplete",  # Valid status per DB constraint
        billing_interval="monthly",
        amount_cents=1900,
        currency="USD",
        current_period_start=datetime.now() - timedelta(days=30),
        current_period_end=datetime.now()
    )
    db_session.add(subscription)
    await db_session.flush()
    
    assert subscription.id is not None
    assert subscription.status == "incomplete"


@pytest.mark.asyncio
async def test_active_subscription_created_correctly(db_session, b2c_billing_user):
    """Test that an active subscription can be created with correct RLS context"""
    
    await rls_service.set_user_context(db_session, b2c_billing_user['user'].id)
    
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
        current_period_end=datetime.now() + timedelta(days=30)
    )
    db_session.add(subscription)
    await db_session.flush()
    
    assert subscription.id is not None
    assert subscription.status == "active"


@pytest.mark.asyncio
async def test_subscription_rls_prevents_cross_user_visibility(db_session, b2c_billing_user):
    """Test that RLS prevents a user from seeing another user's subscription via query"""
    from tests.conftest import create_b2c_user, create_b2c_workspace
    from sqlalchemy import select
    
    # Create first user's subscription
    await rls_service.set_user_context(db_session, b2c_billing_user['user'].id)
    
    subscription = Subscription(
        workspace_id=b2c_billing_user["workspace"].id,
        user_id=b2c_billing_user["user"].id,
        provider_customer_id=f"cus_{uuid4().hex[:12]}",
        provider_subscription_id=f"sub_{uuid4().hex[:12]}",
        tier="premium",
        status="active"
    )
    db_session.add(subscription)
    await db_session.flush()
    
    # Create a second user
    other_email = f"other-{uuid4().hex[:8]}@b2c.test"
    other_uid = f"firebase-{uuid4().hex[:12]}"
    other_user = await create_b2c_user(db_session, other_email, other_uid, "Other User")
    
    # Switch to other user's context
    await rls_service.set_user_context(db_session, other_user.id)
    
    # Query subscriptions - should be empty for this user
    result = await db_session.execute(select(Subscription))
    visible_subs = result.scalars().all()
    
    assert len(visible_subs) == 0, "RLS VIOLATION: User can see another user's subscription"
