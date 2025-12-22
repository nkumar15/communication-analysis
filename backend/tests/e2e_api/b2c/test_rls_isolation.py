"""
E2E Tests for B2C RLS (Row Level Security) Data Isolation

These tests verify that users cannot access each other's data when RLS is enforced.
Each test creates two separate users and verifies data isolation.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy import select

from tests.conftest import (
    create_b2c_user,
    create_b2c_workspace,
    create_b2c_mock_token,
    encode_mock_jwt
)
from modules.b2c.models.subscription import Subscription, Invoice, PaymentMethod, CouponRedemption, Coupon
from modules.b2c.models.workspace import Workspace
from core.db.rls import rls_service


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def two_users(db_session):
    """Create two separate B2C users with their own workspaces
    
    Note: Each user is created with their RLS context, then we update
    default_workspace_id with the correct context before flushing.
    """
    from sqlalchemy import text
    
    # User A
    email_a = f"usera-{uuid4().hex[:8]}@b2c.test"
    firebase_uid_a = f"firebase-a-{uuid4().hex[:12]}"
    user_a = await create_b2c_user(db_session, email_a, firebase_uid_a, "User A")
    workspace_a = await create_b2c_workspace(db_session, user_a.id, "User A Workspace", 'personal')
    
    # Set RLS context for User A before updating their record
    await rls_service.set_user_context(db_session, user_a.id)
    user_a.default_workspace_id = workspace_a.id
    await db_session.flush()
    
    # User B
    email_b = f"userb-{uuid4().hex[:8]}@b2c.test"
    firebase_uid_b = f"firebase-b-{uuid4().hex[:12]}"
    user_b = await create_b2c_user(db_session, email_b, firebase_uid_b, "User B")
    workspace_b = await create_b2c_workspace(db_session, user_b.id, "User B Workspace", 'personal')
    
    # Set RLS context for User B before updating their record
    await rls_service.set_user_context(db_session, user_b.id)
    user_b.default_workspace_id = workspace_b.id
    await db_session.flush()
    
    # Create auth tokens
    token_data_a = create_b2c_mock_token(firebase_uid_a, email_a)
    token_data_b = create_b2c_mock_token(firebase_uid_b, email_b)
    
    return {
        "user_a": {
            "user": user_a,
            "workspace": workspace_a,
            "token_data": token_data_a,
            "auth_token": encode_mock_jwt(token_data_a),
            "firebase_uid": firebase_uid_a,
            "email": email_a
        },
        "user_b": {
            "user": user_b,
            "workspace": workspace_b,
            "token_data": token_data_b,
            "auth_token": encode_mock_jwt(token_data_b),
            "firebase_uid": firebase_uid_b,
            "email": email_b
        }
    }


# ============================================================================
# SUBSCRIPTION ISOLATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_user_cannot_see_other_users_subscription_via_direct_query(db_session, two_users):
    """
    Direct database query test: User A's RLS context should not return User B's subscriptions.
    """
    user_a = two_users["user_a"]
    user_b = two_users["user_b"]
    
    # Create subscription for User B
    await rls_service.set_user_context(db_session, user_b['user'].id)
    
    subscription_b = Subscription(
        workspace_id=user_b["workspace"].id,
        user_id=user_b["user"].id,
        status="active"
    )
    db_session.add(subscription_b)
    await db_session.flush()
    
    # Switch to User A's RLS context
    await rls_service.set_user_context(db_session, user_a['user'].id)
    
    # Query all subscriptions - should return EMPTY for User A
    result = await db_session.execute(select(Subscription))
    subscriptions = result.scalars().all()
    
    assert len(subscriptions) == 0, \
        f"RLS VIOLATION: User A can see {len(subscriptions)} subscriptions (expected 0)"


# ============================================================================
# WORKSPACE ISOLATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_user_cannot_see_other_users_workspace(db_session, two_users):
    """
    CRITICAL: User A should NOT be able to access User B's workspace.
    
    This validates RLS policy: workspace_member_access
    """
    user_a = two_users["user_a"]
    user_b = two_users["user_b"]
    
    # Set User A's RLS context
    await rls_service.set_user_context(db_session, user_a['user'].id)
    
    # Query User B's workspace by ID - should fail or return empty
    result = await db_session.execute(
        select(Workspace).where(Workspace.id == user_b["workspace"].id)
    )
    workspace = result.scalar_one_or_none()
    
    assert workspace is None, \
        f"RLS VIOLATION: User A can access User B's workspace!"


@pytest.mark.asyncio
async def test_user_can_only_see_own_workspaces(db_session, two_users):
    """
    Verify User A can only see their own workspace(s).
    """
    user_a = two_users["user_a"]
    
    # Set User A's RLS context
    await rls_service.set_user_context(db_session, user_a['user'].id)
    
    # Query all workspaces - should return only User A's workspace
    result = await db_session.execute(select(Workspace))
    workspaces = result.scalars().all()
    
    assert len(workspaces) == 1, f"Expected 1 workspace, got {len(workspaces)}"
    assert workspaces[0].id == user_a["workspace"].id


# ============================================================================
# PAYMENT METHOD ISOLATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_user_cannot_see_other_users_payment_methods(db_session, two_users):
    """
    CRITICAL: User A should NOT be able to access User B's payment methods.
    
    This validates RLS policy: payment_methods_select_own
    """
    user_a = two_users["user_a"]
    user_b = two_users["user_b"]
    
    # Create payment method for User B
    await rls_service.set_user_context(db_session, user_b['user'].id)
    
    payment_method_b = PaymentMethod(
        user_id=user_b["user"].id,
        provider_payment_method_id=f"pm_{uuid4().hex[:12]}",
        provider_customer_id=f"cus_{uuid4().hex[:12]}",
        type="card",
        card_brand="visa",
        card_last4="4242",
        card_exp_month=12,
        card_exp_year=2025,
        is_default=True
    )
    db_session.add(payment_method_b)
    await db_session.flush()
    
    # Switch to User A's RLS context
    await rls_service.set_user_context(db_session, user_a['user'].id)
    
    # Query all payment methods - should return EMPTY for User A
    result = await db_session.execute(select(PaymentMethod))
    payment_methods = result.scalars().all()
    
    assert len(payment_methods) == 0, \
        f"RLS VIOLATION: User A can see {len(payment_methods)} payment methods (expected 0)"


# ============================================================================
# INSERT/UPDATE POLICY TESTS  
# ============================================================================

@pytest.mark.asyncio
async def test_user_cannot_insert_subscription_for_other_user(db_session, two_users):
    """
    CRITICAL: User A should NOT be able to create a subscription for User B.
    
    This validates RLS policy: subscriptions_insert_own (WITH CHECK)
    """
    user_a = two_users["user_a"]
    user_b = two_users["user_b"]
    
    # Set User A's RLS context
    await rls_service.set_user_context(db_session, user_a['user'].id)
    
    # Try to create subscription for User B - should fail
    malicious_subscription = Subscription(
        workspace_id=user_b["workspace"].id,
        user_id=user_b["user"].id,  # Trying to set someone else's user_id
        status="active"
    )
    db_session.add(malicious_subscription)
    
    # This should raise an error due to RLS WITH CHECK policy
    with pytest.raises(Exception):  # Will be a SQLAlchemy IntegrityError or similar
        await db_session.flush()
    
    await db_session.rollback()


@pytest.mark.asyncio
async def test_user_can_create_own_subscription(db_session, two_users):
    """
    Verify User A CAN create their own subscription.
    """
    user_a = two_users["user_a"]
    
    # Set User A's RLS context
    await rls_service.set_user_context(db_session, user_a['user'].id)
    
    # Create subscription for self - should succeed
    own_subscription = Subscription(
        workspace_id=user_a["workspace"].id,
        user_id=user_a["user"].id,
        status="active"
    )
    db_session.add(own_subscription)
    await db_session.flush()
    
    assert own_subscription.id is not None
    assert own_subscription.user_id == user_a["user"].id
