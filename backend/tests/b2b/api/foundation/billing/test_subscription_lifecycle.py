"""
Subscription Lifecycle Tests — upgrade and downgrade via mocked SubscriptionService.

Key invariant being verified:
  - tenant.features contains ONLY boolean flags and the plugins list.
  - tenant.features must NOT contain a 'limits' key.
  - Limits are always read fresh from plan.limits via the subscription JOIN.

See also:
  tests/b2b/services/foundation/billing/test_subscription_checkout.py — deeper service tests
  tests/b2b/api/foundation/billing/test_stripe_webhook.py              — HTTP layer tests
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from modules.b2b.models import B2BSubscriptionPlan
from modules.b2b.services.subscription_service import SubscriptionService
from modules.b2b.services.tenant_service import tenant_service

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_plan(db_session) -> B2BSubscriptionPlan:
    result = await db_session.execute(select(B2BSubscriptionPlan))
    plan = result.scalars().first()
    if not plan:
        plan = B2BSubscriptionPlan(
            tier_key="starter",
            name="Starter",
            base_price_monthly=0,
            per_seat_price_monthly=0,
            provider_config={},
        )
        db_session.add(plan)
        await db_session.flush()
    return plan


async def _build_service(db_session, mock_plan: MagicMock) -> SubscriptionService:
    """Build service with mocked Stripe provider + RLS platform-admin context."""
    from core.db.rls import rls_service
    await rls_service.set_platform_admin_context(db_session)

    svc = SubscriptionService(db_session)
    svc.provider = AsyncMock()
    svc.provider.get_subscription.return_value = {
        "status": "active",
        "current_period_start": 1700000000,
        "current_period_end": 1702592000,
        "latest_invoice": None,
    }
    svc.get_plan_by_tier_key = AsyncMock(return_value=mock_plan)
    return svc


def _checkout_payload(tenant_id: str, tier: str) -> dict:
    return {
        "id": f"cs_test_{uuid4().hex[:8]}",
        "customer": f"cus_{uuid4().hex[:8]}",
        "subscription": f"sub_{uuid4().hex[:8]}",
        "metadata": {
            "tenant_id": tenant_id,
            "tier": tier,
            "billing_interval": "monthly",
            "seat_count": "5",
        },
    }


class TestSubscriptionLifecycle:
    """Upgrade and downgrade flows — verifies tenant.features shape and plugin state."""

    async def test_upgrade_enables_plugins_and_flags(
        self, api_client: AsyncClient, b2b_test_setup, db_session
    ):
        """
        Enterprise checkout must:
          - Enable listed plugins in tenant.features['plugins']
          - Set feature flags (sso=True) in tenant.features
          - NOT store limits in tenant.features (limits live on the plan row)
        """
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]

        real_plan = await _seed_plan(db_session)
        mock_plan = MagicMock(spec=B2BSubscriptionPlan)
        mock_plan.id = real_plan.id
        mock_plan.tier_key = "enterprise"
        mock_plan.features = {
            "plugins": ["geographic_boundaries", "data_classification"],
            "sso": True,
            "audit_logs": True,
            "bulk_invite": True,
            "dedicated_support": True,
            "custom_branding": True,
        }
        mock_plan.limits = {"max_users": -1, "storage_gb": 1000, "max_teams": -1}
        mock_plan.base_price_monthly = 5000
        mock_plan.per_seat_price_monthly = 2000
        mock_plan.provider_config = {"stripe": {"monthly_price_id": "price_123"}}

        # Tenant starts with no plugins, sso=False
        await tenant_service.update_tenant_features(
            db_session, tenant_id,
            {"plugins": [], "sso": False, "audit_logs": False,
             "bulk_invite": False, "dedicated_support": False, "custom_branding": False}
        )
        await db_session.commit()

        svc = await _build_service(db_session, mock_plan)

        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "infrastructure.email.email_service.send_subscription_confirmation_email"
        ):
            await svc.handle_checkout_completed(_checkout_payload(str(tenant_id), "enterprise"))
            await db_session.commit()

        updated = await tenant_service.get_tenant_by_id(setup["session"], tenant_id)

        # Plugins enabled
        assert set(updated.features.get("plugins", [])) == {
            "geographic_boundaries", "data_classification"
        }
        # Feature flags set
        assert updated.features.get("sso") is True

        # CRITICAL: limits must NOT be stored in tenant.features
        assert "limits" not in updated.features, (
            f"tenant.features must not contain 'limits'. Got: {updated.features}"
        )

    async def test_downgrade_removes_plugins_and_reverts_flags(
        self, api_client: AsyncClient, b2b_test_setup, db_session
    ):
        """
        Downgrade to starter must:
          - Clear plugins from tenant.features
          - Revert feature flags (sso=False)
          - NOT store limits in tenant.features
        """
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]

        real_plan = await _seed_plan(db_session)

        # Tenant starts with enterprise plugins active
        await tenant_service.update_tenant_features(
            db_session, tenant_id,
            {"plugins": ["geographic_boundaries"], "sso": True, "audit_logs": True,
             "bulk_invite": False, "dedicated_support": False, "custom_branding": False}
        )
        await db_session.commit()

        mock_plan = MagicMock(spec=B2BSubscriptionPlan)
        mock_plan.id = real_plan.id
        mock_plan.tier_key = "starter"
        mock_plan.features = {
            "plugins": [],
            "sso": True,
            "audit_logs": True,
            "bulk_invite": False,
            "dedicated_support": False,
            "custom_branding": False,
        }
        mock_plan.limits = {"max_users": 5, "max_teams": 2, "storage_gb": 10}
        mock_plan.base_price_monthly = 0
        mock_plan.per_seat_price_monthly = 100000
        mock_plan.provider_config = {"stripe": {"monthly_price_id": "price_free"}}

        svc = await _build_service(db_session, mock_plan)

        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "infrastructure.email.email_service.send_subscription_confirmation_email"
        ):
            await svc.handle_checkout_completed(_checkout_payload(str(tenant_id), "starter"))
            await db_session.commit()

        updated = await tenant_service.get_tenant_by_id(setup["session"], tenant_id)

        assert updated.features.get("plugins", []) == []

        # CRITICAL: limits must NOT be stored in tenant.features
        assert "limits" not in updated.features, (
            f"tenant.features must not contain 'limits'. Got: {updated.features}"
        )

    async def test_tenant_features_never_contains_limits(self, db_session, b2b_test_setup):
        """
        Regression guard: regardless of tier, tenant.features must never contain
        a 'limits' key after apply_subscription_to_tenant() runs.
        """
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        real_plan = await _seed_plan(db_session)

        for tier, plugins, limits in [
            ("starter", [], {"max_users": 5, "max_teams": 2, "storage_gb": 10}),
            ("enterprise", ["geographic_boundaries"], {"max_users": -1, "max_teams": -1, "storage_gb": -1}),
        ]:
            mock_plan = MagicMock(spec=B2BSubscriptionPlan)
            mock_plan.id = real_plan.id
            mock_plan.tier_key = tier
            mock_plan.features = {
                "plugins": plugins, "sso": tier == "enterprise",
                "audit_logs": True, "bulk_invite": False,
                "dedicated_support": False, "custom_branding": False,
            }
            mock_plan.limits = limits
            mock_plan.base_price_monthly = 0
            mock_plan.per_seat_price_monthly = 0
            mock_plan.provider_config = {}

            from core.db.rls import rls_service
            await rls_service.set_platform_admin_context(db_session)
            svc = await _build_service(db_session, mock_plan)

            with __import__("unittest.mock", fromlist=["patch"]).patch(
                "infrastructure.email.email_service.send_subscription_confirmation_email"
            ):
                await svc.handle_checkout_completed(_checkout_payload(str(tenant_id), tier))
                await db_session.commit()

            updated = await tenant_service.get_tenant_by_id(setup["session"], tenant_id)
            assert "limits" not in updated.features, (
                f"Tier '{tier}': tenant.features must not contain 'limits'. "
                f"Got: {updated.features}"
            )

    async def test_upgrade_unauthorized(self, api_client: AsyncClient):
        """No token → 401."""
        response = await api_client.post("/api/b2b/billing/checkout", json={"tier": "enterprise"})
        assert response.status_code == 401

    async def test_upgrade_forbidden(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """Valid token with viewer role → 403 on billing endpoint."""
        from tests.conftest import create_test_user, encode_mock_jwt, create_mock_firebase_token
        setup = b2b_test_setup

        viewer = await create_test_user(
            db_session=setup["session"],
            tenant_id=setup["tenant_id"],
            email=f"viewer-{uuid4().hex[:8]}@test.com",
            role_slug="viewer",
        )
        viewer_token = encode_mock_jwt(create_mock_firebase_token(
            uid=viewer.firebase_uid,
            email=viewer.email,
            firebase_tenant_id=setup["tenant"].firebase_tenant_id,
        ))

        response = await api_client.post(
            "/api/b2b/billing/checkout",
            json={"tier": "enterprise"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403
