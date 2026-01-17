import pytest
from httpx import AsyncClient
from sqlalchemy import select
from modules.b2b.models import TenantModel, B2BSubscriptionPlan, Subscription
from modules.b2b.services.subscription_service import SubscriptionService
from modules.b2b.services.tenant_service import tenant_service
from unittest.mock import MagicMock, AsyncMock

@pytest.mark.asyncio
class TestSubscriptionLifecycle:
    
    async def test_upgrade_enables_plugins(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """
        Test that upgrading a subscription synchronizes plugins from the Plan to the Tenant.
        """
        tenant_id = b2b_test_setup["tenant_id"]
        
    async def test_upgrade_enables_plugins(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """
        Test that upgrading a subscription synchronizes plugins, limits, and features from the Plan to the Tenant.
        """
        tenant_id = b2b_test_setup["tenant_id"]
        
        # Fetch a REAL plan ID to satisfy Foreign Key constraints
        result = await db_session.execute(select(B2BSubscriptionPlan))
        real_plan = result.scalars().first()
        if not real_plan:
             # Create one if missing (fallback)
             real_plan = B2BSubscriptionPlan(
                 tier_key="starter", 
                 name="Starter",
                 base_price_monthly=0,per_seat_price_monthly=0
             )
             db_session.add(real_plan)
             await db_session.flush()

        # 3. Simulate: Subscription Upgrade (via Service)
        sub_service = SubscriptionService(db_session)
        sub_service.provider = AsyncMock()
        sub_service.provider.get_subscription.return_value = {
            "status": "active",
            "current_period_end": 1234567890
        }

        # MOCK the plan retrieval to return our custom features without touching DB
        mock_plan = MagicMock()
        mock_plan.id = real_plan.id # Use REAL ID
        mock_plan.tier_key = "enterprise"
        
        # MOCK Features & Limits
        mock_plan.features = {"plugins": ["geographic_boundaries", "data_classification"], "sso": True}
        mock_plan.limits = {"max_users": -1, "storage_gb": 1000}
        
        # We also need these for pricing calc
        mock_plan.base_price_monthly = 1000
        mock_plan.per_seat_price_monthly = 500
        mock_plan.provider_config = {"stripe": {"monthly_price_id": "price_123"}} 
        
        sub_service.get_plan_by_tier_key = AsyncMock(return_value=mock_plan)
        
        # 2. Setup: Ensure Tenant initially has NO plugins and basic limits/features
        # Simulate 'Starter' state
        current_features = {"plugins": [], "sso": False}
        current_limits = {"max_users": 5}
        # We manually set this via our new service method to prep the state
        await tenant_service.update_tenant_subscription_config(db_session, tenant_id, current_features, current_limits)
        
        tenant = await tenant_service.get_tenant_by_id(db_session, tenant_id)
        assert tenant.features.get("plugins") == []
        assert tenant.features.get("sso") is False
        assert tenant.features.get("limits", {}).get("max_users") == 5
        
        # Mock payload from Stripe Webhook - MUST USE VALID TIER ENUM VALUE
        webhook_payload = {
            "metadata": {
                "tenant_id": str(tenant_id),
                "tier": "enterprise", # Valid Enum
                "billing_interval": "monthly",
                "seat_count": 5
            },
            "subscription": "sub_123",
            "customer": "cus_123"
        }
        
        # ACTION: Handle Checkout Completion
        await sub_service.handle_checkout_completed(webhook_payload)
        
        # 4. Verify: Tenant now has plugins, sso, and unlimited users
        # Need to refresh tenant from DB
        updated_tenant = await tenant_service.get_tenant_by_id(db_session, tenant_id)
        plugins = updated_tenant.features.get("plugins", [])
        
        assert "geographic_boundaries" in plugins
        assert "data_classification" in plugins
        assert len(plugins) == 2
        
        # Verify Features
        assert updated_tenant.features.get("sso") is True
        
        # Verify Limits
        limits = updated_tenant.features.get("limits", {})
        assert limits.get("max_users") == -1
        assert limits.get("storage_gb") == 1000

    async def test_downgrade_disables_plugins(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """
        Test that downgrading (changing plan) removes plugins not in the new plan.
        """
        tenant_id = b2b_test_setup["tenant_id"]
        
    async def test_downgrade_disables_plugins(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """
        Test that downgrading (changing plan) removes plugins not in the new plan.
        """
    async def test_downgrade_disables_plugins(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """
        Test that downgrading (changing plan) removes plugins and reverts limits.
        """
        tenant_id = b2b_test_setup["tenant_id"]
        
        # Fetch a REAL plan ID
        result = await db_session.execute(select(B2BSubscriptionPlan))
        real_plan = result.scalars().first()
        if not real_plan:
             real_plan = B2BSubscriptionPlan(
                 tier_key="starter", 
                 name="Starter",
                 base_price_monthly=0,per_seat_price_monthly=0,
                 provider_config={}
             )
             db_session.add(real_plan)
             await db_session.flush()

        # 2. Setup: Tenant CURRENTLY has plugins, SSO, and high limits (from previous upgrade)
        # Use our new method to prep state
        current_features = {"plugins": ["geographic_boundaries"], "sso": True}
        current_limits = {"max_users": 100}
        await tenant_service.update_tenant_subscription_config(db_session, tenant_id, current_features, current_limits)
        
        await db_session.flush()

        # 3. Simulate: Downgrade to Starter
        sub_service = SubscriptionService(db_session)
        sub_service.provider = AsyncMock()
        sub_service.provider.get_subscription.return_value = {"status": "active"}

        # MOCK Plan as Starter with NO plugins, NO SSO, low limits
        mock_plan = MagicMock()
        mock_plan.id = real_plan.id # Use REAL ID
        mock_plan.tier_key = "starter"
        mock_plan.features = {"plugins": [], "sso": False}
        mock_plan.limits = {"max_users": 5, "max_teams": 1}
        
        mock_plan.base_price_monthly = 0
        mock_plan.per_seat_price_monthly = 0
        mock_plan.provider_config = {"stripe": {"monthly_price_id": "price_free"}}

        sub_service.get_plan_by_tier_key = AsyncMock(return_value=mock_plan)

        webhook_payload = {
            "metadata": {
                "tenant_id": str(tenant_id),
                "tier": "starter", # Valid Enum
                "billing_interval": "monthly"
            },
            "subscription": "sub_456",
            "customer": "cus_123"
        }
        
        await sub_service.handle_checkout_completed(webhook_payload)
        
        # 4. Verify: Tenant has NO plugins, NO SSO, and 5 users limit
        updated_tenant = await tenant_service.get_tenant_by_id(db_session, tenant_id)
        plugins = updated_tenant.features.get("plugins", [])
        
        assert "geographic_boundaries" not in plugins
        assert len(plugins) == 0
        
        assert updated_tenant.features.get("sso") is False
        
        limits = updated_tenant.features.get("limits", {})
        assert limits.get("max_users") == 5
        assert limits.get("max_teams") == 1
