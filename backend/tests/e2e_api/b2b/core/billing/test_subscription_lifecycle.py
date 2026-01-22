import pytest
from httpx import AsyncClient
from sqlalchemy import select
from modules.b2b.models import B2BSubscriptionPlan
from modules.b2b.services.subscription_service import SubscriptionService
from modules.b2b.services.tenant_service import tenant_service
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

@pytest.mark.asyncio
class TestSubscriptionLifecycle:
    """
    Standardized tests for subscription upgrade and downgrade flows.
    Follows pytest-testing.md rules: Class-based, AAA pattern, RLS compliant.
    """
    
    async def test_upgrade_enables_plugins_success(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """
        Test that upgrading a subscription synchronizes plugins, limits, and features from the Plan to the Tenant.
        """
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        tenant_session = setup["session"]
        
        # Fetch a REAL plan ID to satisfy Foreign Key constraints
        result = await db_session.execute(select(B2BSubscriptionPlan))
        real_plan = result.scalars().first()
        if not real_plan:
             real_plan = B2BSubscriptionPlan(
                 tier_key="starter", 
                 name="Starter",
                 base_price_monthly=0,
                 per_seat_price_monthly=0
             )
             db_session.add(real_plan)
             await db_session.flush()

        # Simulate: Subscription Upgrade (via Service)
        sub_service = SubscriptionService(db_session)
        sub_service.provider = AsyncMock()
        sub_service.provider.get_subscription.return_value = {
            "status": "active",
            "current_period_end": 1234567890
        }

        # Mock the plan retrieval to return our custom features
        mock_plan = MagicMock()
        mock_plan.id = real_plan.id
        mock_plan.tier_key = "enterprise"
        mock_plan.features = {"plugins": ["geographic_boundaries", "data_classification"], "sso": True}
        mock_plan.limits = {"max_users": -1, "storage_gb": 1000}
        mock_plan.base_price_monthly = 1000
        mock_plan.per_seat_price_monthly = 500
        mock_plan.provider_config = {"stripe": {"monthly_price_id": "price_123"}} 
        
        sub_service.get_plan_by_tier_key = AsyncMock(return_value=mock_plan)
        
        # Ensure Tenant initially has NO plugins
        current_features = {"plugins": [], "sso": False, "limits": {"max_users": 5}}
        await tenant_service.update_tenant_features(db_session, tenant_id, current_features)
        
        # Act
        webhook_payload = {
            "metadata": {
                "tenant_id": str(tenant_id),
                "tier": "enterprise",
                "billing_interval": "monthly",
                "seat_count": 5
            },
            "subscription": "sub_123",
            "customer": "cus_123"
        }
        await sub_service.handle_checkout_completed(webhook_payload)
        
        # Assert: Verify via TenantAwareSession
        updated_tenant = await tenant_service.get_tenant_by_id(tenant_session, tenant_id)
        plugins = updated_tenant.features.get("plugins", [])
        
        assert "geographic_boundaries" in plugins
        assert "data_classification" in plugins
        assert len(plugins) == 2
        assert updated_tenant.features.get("sso") is True
        
        limits = updated_tenant.features.get("limits", {})
        assert limits.get("max_users") == -1
        assert limits.get("storage_gb") == 1000

    async def test_downgrade_disables_plugins_success(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """
        Test that downgrading (changing plan) removes plugins and reverts limits.
        """
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        tenant_session = setup["session"]
        
        # Fetch a REAL plan ID
        result = await db_session.execute(select(B2BSubscriptionPlan))
        real_plan = result.scalars().first()
        if not real_plan:
             real_plan = B2BSubscriptionPlan(
                 tier_key="starter", 
                 name="Starter",
                 base_price_monthly=0,
                 per_seat_price_monthly=0,
                 provider_config={}
             )
             db_session.add(real_plan)
             await db_session.flush()

        # Tenant CURRENTLY has plugins and SSO
        current_features = {"plugins": ["geographic_boundaries"], "sso": True, "limits": {"max_users": 100}}
        await tenant_service.update_tenant_features(db_session, tenant_id, current_features)
        
        # Simulate: Downgrade
        sub_service = SubscriptionService(db_session)
        sub_service.provider = AsyncMock()
        sub_service.provider.get_subscription.return_value = {"status": "active"}

        mock_plan = MagicMock()
        mock_plan.id = real_plan.id
        mock_plan.tier_key = "starter"
        mock_plan.features = {"plugins": [], "sso": False}
        mock_plan.limits = {"max_users": 5, "max_teams": 1}
        mock_plan.base_price_monthly = 0
        mock_plan.per_seat_price_monthly = 0
        mock_plan.provider_config = {"stripe": {"monthly_price_id": "price_free"}}

        sub_service.get_plan_by_tier_key = AsyncMock(return_value=mock_plan)

        # Act
        webhook_payload = {
            "metadata": {
                "tenant_id": str(tenant_id),
                "tier": "starter",
                "billing_interval": "monthly"
            },
            "subscription": "sub_456",
            "customer": "cus_123"
        }
        await sub_service.handle_checkout_completed(webhook_payload)
        
        # Assert: Verify via TenantAwareSession
        updated_tenant = await tenant_service.get_tenant_by_id(tenant_session, tenant_id)
        plugins = updated_tenant.features.get("plugins", [])
        
        assert "geographic_boundaries" not in plugins
        assert len(plugins) == 0
        assert updated_tenant.features.get("sso") is False
        
        limits = updated_tenant.features.get("limits", {})
        assert limits.get("max_users") == 5
        assert limits.get("max_teams") == 1

    async def test_upgrade_unauthorized(self, api_client: AsyncClient):
        """Rule 7: No token (401)"""
        # Endpoint for checkout/upgrade
        response = await api_client.post("/api/b2b/billing/checkout", json={"tier": "enterprise"})
        assert response.status_code == 401

    async def test_upgrade_forbidden(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """Rule 7: Valid token, but insufficient permission (403)"""
        from tests.conftest import create_test_user
        setup = b2b_test_setup
        
        # Create a user with 'viewer' role (no billing permissions)
        viewer = await create_test_user(
            db_session=setup["session"],
            tenant_id=setup["tenant_id"],
            email=f"viewer-{uuid4().hex[:8]}@test.com",
            role_slug="viewer"
        )
        from tests.conftest import encode_mock_jwt, create_mock_firebase_token
        viewer_token = encode_mock_jwt(create_mock_firebase_token(
            uid=viewer.firebase_uid,
            email=viewer.email,
            firebase_tenant_id=setup["tenant"].firebase_tenant_id
        ))
        
        response = await api_client.post(
            "/api/b2b/billing/checkout", 
            json={"tier": "enterprise"},
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        # Note: B2B billing might be restricted to 'owner' or specific billing roles.
        assert response.status_code == 403
