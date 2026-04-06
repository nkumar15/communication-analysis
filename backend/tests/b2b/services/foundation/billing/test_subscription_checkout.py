"""
Service Layer: Stripe Checkout → Plugin Activation

Tests handle_checkout_completed() in isolation with a mocked Stripe provider.
Covers two scenarios the seed-based tests cannot:
  1. All 3 enterprise plugins enabled in a single checkout
  2. Plugin lifecycle hooks (on_tenant_enable) actually called
  3. Downgrade from enterprise → starter removes plugins
  4. Idempotent checkout (second call for same tenant)
  5. Email failure does not roll back subscription

See also:
  tests/b2b/api/foundation/billing/test_stripe_webhook.py  — webhook endpoint tests
  tests/b2b/api/use_cases/bank_surveillance/test_plugin_integration.py — bank plugin hooks
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from modules.b2b.models import B2BSubscriptionPlan, B2BSubscription as Subscription
from modules.b2b.services.subscription_service import SubscriptionService
from modules.b2b.services.tenant_service import tenant_service

pytestmark = pytest.mark.asyncio

ENTERPRISE_PLUGINS = ["geographic_boundaries", "hierarchical_teams", "data_classification"]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_checkout_session(tenant_id: str, tier: str = "enterprise", seats: int = 5) -> dict:
    """Build a fake Stripe checkout.session.completed payload."""
    return {
        "id": f"cs_test_{uuid4().hex[:8]}",
        "customer": f"cus_{uuid4().hex[:8]}",
        "subscription": f"sub_{uuid4().hex[:8]}",
        "metadata": {
            "tenant_id": tenant_id,
            "tier": tier,
            "billing_interval": "monthly",
            "seat_count": str(seats),
        },
    }


def _mock_plan(tier: str, plugins: list, real_plan_id) -> MagicMock:
    """Build a mock B2BSubscriptionPlan with the given tier and plugins."""
    plan = MagicMock(spec=B2BSubscriptionPlan)
    plan.id = real_plan_id
    plan.tier_key = tier
    plan.features = {"plugins": plugins, "sso": tier == "enterprise", "audit_logs": True}
    plan.limits = {
        "max_users": -1 if tier == "enterprise" else 5,
        "max_teams": -1 if tier == "enterprise" else 2,
        "storage_gb": 1000 if tier == "enterprise" else 10,
    }
    plan.base_price_monthly = 0 if tier == "starter" else 5000
    plan.per_seat_price_monthly = 0 if tier == "starter" else 2000
    plan.provider_config = {"stripe": {"monthly_price_id": "price_mock"}}
    return plan


async def _build_service(db_session, mock_plan: MagicMock) -> SubscriptionService:
    """Build a SubscriptionService with mocked Stripe provider and plan lookup.

    Sets platform-admin RLS context so subscription INSERTs bypass row-level
    security — matching the production webhook handler behaviour.
    """
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


async def _seed_plan(db_session) -> B2BSubscriptionPlan:
    """Return the first seeded plan, or create a minimal one for FK compliance."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Test Classes
# ─────────────────────────────────────────────────────────────────────────────

class TestEnterpriseCheckoutActivatesPlugins:
    """
    Enterprise checkout must enable all 3 bank plugins on the tenant.
    Uses mocked Stripe provider; verifies outcome via real DB.
    """

    async def test_checkout_enables_all_enterprise_plugins(self, db_session, b2b_test_setup):
        """
        Happy path: enterprise checkout writes all 3 plugins into tenant.features['plugins'].
        """
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        real_plan = await _seed_plan(db_session)
        mock_plan = _mock_plan("enterprise", ENTERPRISE_PLUGINS, real_plan.id)

        # Tenant starts with no plugins
        await tenant_service.update_tenant_features(db_session, tenant_id, {"plugins": []})
        await db_session.commit()

        svc = await _build_service(db_session, mock_plan)
        session_data = _make_checkout_session(str(tenant_id), tier="enterprise")

        # Act
        with patch("infrastructure.email.email_service.send_subscription_confirmation_email"):
            await svc.handle_checkout_completed(session_data)
            await db_session.commit()

        # Assert — all 3 plugins active
        updated = await tenant_service.get_tenant_by_id(setup["session"], tenant_id)
        active_plugins = set(updated.features.get("plugins", []))

        assert active_plugins == set(ENTERPRISE_PLUGINS), (
            f"Expected {ENTERPRISE_PLUGINS}, got {sorted(active_plugins)}"
        )

    async def test_checkout_enables_sso_and_limits(self, db_session, b2b_test_setup):
        """
        Enterprise checkout also syncs non-plugin features (sso, limits) to the tenant.
        """
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        real_plan = await _seed_plan(db_session)
        mock_plan = _mock_plan("enterprise", ENTERPRISE_PLUGINS, real_plan.id)

        svc = await _build_service(db_session, mock_plan)
        session_data = _make_checkout_session(str(tenant_id), tier="enterprise")

        # Act
        with patch("infrastructure.email.email_service.send_subscription_confirmation_email"):
            await svc.handle_checkout_completed(session_data)
            await db_session.commit()

        # Assert
        updated = await tenant_service.get_tenant_by_id(setup["session"], tenant_id)
        assert updated.features.get("sso") is True
        assert updated.features["limits"]["max_users"] == -1
        assert updated.features["limits"]["max_teams"] == -1

    async def test_checkout_calls_on_tenant_enable_for_each_plugin(
        self, db_session, b2b_test_setup
    ):
        """
        on_tenant_enable() must be called exactly once for each newly added plugin.
        Verifies the lifecycle hook wiring, not the hook implementation.
        """
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        real_plan = await _seed_plan(db_session)
        mock_plan = _mock_plan("enterprise", ENTERPRISE_PLUGINS, real_plan.id)

        await tenant_service.update_tenant_features(db_session, tenant_id, {"plugins": []})
        await db_session.commit()

        svc = await _build_service(db_session, mock_plan)
        session_data = _make_checkout_session(str(tenant_id), tier="enterprise")

        hook_calls: list[str] = []

        async def spy_on_tenant_enable(t_id: str, db):
            hook_calls.append(t_id)

        with (
            patch("infrastructure.email.email_service.send_subscription_confirmation_email"),
            patch(
                "plugins.geographic_boundaries.plugin.GeographicBoundariesPlugin.on_tenant_enable",
                side_effect=spy_on_tenant_enable,
            ),
            patch(
                "plugins.hierarchical_teams.plugin.HierarchicalTeamsPlugin.on_tenant_enable",
                side_effect=spy_on_tenant_enable,
            ),
            patch(
                "plugins.data_classification.plugin.DataClassificationPlugin.on_tenant_enable",
                side_effect=spy_on_tenant_enable,
            ),
        ):
            await svc.handle_checkout_completed(session_data)
            await db_session.commit()

        # Each plugin's hook called exactly once
        assert len(hook_calls) == 3, f"Expected 3 hook calls, got {len(hook_calls)}"

    async def test_checkout_creates_subscription_record(self, db_session, b2b_test_setup):
        """
        checkout.session.completed must persist a Subscription row in the DB.
        """
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        real_plan = await _seed_plan(db_session)
        mock_plan = _mock_plan("enterprise", ENTERPRISE_PLUGINS, real_plan.id)

        svc = await _build_service(db_session, mock_plan)
        session_data = _make_checkout_session(str(tenant_id), tier="enterprise", seats=10)

        # Act
        with patch("infrastructure.email.email_service.send_subscription_confirmation_email"):
            subscription = await svc.handle_checkout_completed(session_data)
            await db_session.commit()

        # Assert
        assert subscription is not None
        assert subscription.tier == "enterprise"
        assert subscription.seat_count == 10
        assert subscription.status == "active"


class TestSubscriptionDowngradeRemovesPlugins:
    """
    Downgrading from enterprise → starter must remove plugins from tenant.features.
    Plugin data in DB must NOT be deleted (safe downgrade).
    """

    async def test_downgrade_removes_all_plugins(self, db_session, b2b_test_setup):
        """
        Downgrade from enterprise (3 plugins) to starter (0 plugins).
        tenant.features['plugins'] must be empty after downgrade.
        """
        # Arrange: tenant starts on enterprise with all plugins active
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        real_plan = await _seed_plan(db_session)

        await tenant_service.update_tenant_features(
            db_session, tenant_id, {"plugins": ENTERPRISE_PLUGINS, "sso": True}
        )
        await db_session.commit()

        mock_starter = _mock_plan("starter", [], real_plan.id)
        svc = await _build_service(db_session, mock_starter)
        session_data = _make_checkout_session(str(tenant_id), tier="starter")

        # Act
        with patch("infrastructure.email.email_service.send_subscription_confirmation_email"):
            await svc.handle_checkout_completed(session_data)
            await db_session.commit()

        # Assert
        updated = await tenant_service.get_tenant_by_id(setup["session"], tenant_id)
        assert updated.features.get("plugins", []) == []
        assert updated.features.get("sso") is False

    async def test_downgrade_calls_on_tenant_disable_for_each_plugin(
        self, db_session, b2b_test_setup
    ):
        """
        on_tenant_disable() must be called for each removed plugin during downgrade.
        """
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        real_plan = await _seed_plan(db_session)

        await tenant_service.update_tenant_features(
            db_session, tenant_id, {"plugins": ENTERPRISE_PLUGINS}
        )
        await db_session.commit()

        mock_starter = _mock_plan("starter", [], real_plan.id)
        svc = await _build_service(db_session, mock_starter)
        session_data = _make_checkout_session(str(tenant_id), tier="starter")

        disable_calls: list[str] = []

        async def spy_on_tenant_disable(t_id: str, db):
            disable_calls.append(t_id)

        with (
            patch("infrastructure.email.email_service.send_subscription_confirmation_email"),
            patch(
                "plugins.geographic_boundaries.plugin.GeographicBoundariesPlugin.on_tenant_disable",
                side_effect=spy_on_tenant_disable,
            ),
            patch(
                "plugins.hierarchical_teams.plugin.HierarchicalTeamsPlugin.on_tenant_disable",
                side_effect=spy_on_tenant_disable,
            ),
            patch(
                "plugins.data_classification.plugin.DataClassificationPlugin.on_tenant_disable",
                side_effect=spy_on_tenant_disable,
            ),
        ):
            await svc.handle_checkout_completed(session_data)
            await db_session.commit()

        assert len(disable_calls) == 3

    async def test_partial_upgrade_only_enables_new_plugins(self, db_session, b2b_test_setup):
        """
        If tenant already has geographic_boundaries, upgrading to enterprise
        must call on_tenant_enable only for the two new plugins.
        """
        # Arrange: tenant already has geo plugin
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        real_plan = await _seed_plan(db_session)

        await tenant_service.update_tenant_features(
            db_session, tenant_id, {"plugins": ["geographic_boundaries"]}
        )
        await db_session.commit()

        mock_enterprise = _mock_plan("enterprise", ENTERPRISE_PLUGINS, real_plan.id)
        svc = await _build_service(db_session, mock_enterprise)
        session_data = _make_checkout_session(str(tenant_id), tier="enterprise")

        enable_calls: list[str] = []

        async def spy_enable(plugin_name: str):
            async def _inner(t_id: str, db):
                enable_calls.append(plugin_name)
            return _inner

        with (
            patch("infrastructure.email.email_service.send_subscription_confirmation_email"),
            patch(
                "plugins.geographic_boundaries.plugin.GeographicBoundariesPlugin.on_tenant_enable",
                side_effect=await spy_enable("geographic_boundaries"),
            ),
            patch(
                "plugins.hierarchical_teams.plugin.HierarchicalTeamsPlugin.on_tenant_enable",
                side_effect=await spy_enable("hierarchical_teams"),
            ),
            patch(
                "plugins.data_classification.plugin.DataClassificationPlugin.on_tenant_enable",
                side_effect=await spy_enable("data_classification"),
            ),
        ):
            await svc.handle_checkout_completed(session_data)
            await db_session.commit()

        # Only the 2 NEW plugins should have been enabled
        assert "geographic_boundaries" not in enable_calls, (
            "geo already enabled — hook must NOT fire again"
        )
        assert set(enable_calls) == {"hierarchical_teams", "data_classification"}


class TestCheckoutIdempotency:
    """
    A second checkout.session.completed for the same tenant must not corrupt state.
    """

    async def test_second_checkout_same_tier_is_safe(self, db_session, b2b_test_setup):
        """
        Processing the same enterprise checkout twice must produce the same result.
        No duplicate plugin rows, no exception.
        """
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        real_plan = await _seed_plan(db_session)
        mock_plan = _mock_plan("enterprise", ENTERPRISE_PLUGINS, real_plan.id)

        svc = await _build_service(db_session, mock_plan)
        session_data = _make_checkout_session(str(tenant_id), tier="enterprise")

        with patch("infrastructure.email.email_service.send_subscription_confirmation_email"):
            await svc.handle_checkout_completed(session_data)
            await db_session.commit()

            # Second identical checkout (e.g. Stripe retry).
            # RLS SET LOCAL resets on commit, so re-establish platform-admin context
            # exactly as a second webhook HTTP request would.
            from core.db.rls import rls_service
            await rls_service.set_platform_admin_context(db_session)
            await svc.handle_checkout_completed(session_data)
            await db_session.commit()

        # Assert: plugins still exactly ENTERPRISE_PLUGINS — no duplicates
        updated = await tenant_service.get_tenant_by_id(setup["session"], tenant_id)
        active_plugins = updated.features.get("plugins", [])
        assert set(active_plugins) == set(ENTERPRISE_PLUGINS)
        assert len(active_plugins) == len(set(active_plugins)), "Duplicate plugins detected"

    async def test_email_failure_does_not_abort_subscription(self, db_session, b2b_test_setup):
        """
        Email send failure must NOT roll back the subscription or plugin activation.
        """
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        real_plan = await _seed_plan(db_session)
        mock_plan = _mock_plan("enterprise", ENTERPRISE_PLUGINS, real_plan.id)

        svc = await _build_service(db_session, mock_plan)
        session_data = _make_checkout_session(str(tenant_id), tier="enterprise")

        with patch(
            "infrastructure.email.email_service.send_subscription_confirmation_email",
            side_effect=Exception("SMTP timeout"),
        ):
            # Must not raise even if email fails
            await svc.handle_checkout_completed(session_data)
            await db_session.commit()

        # Plugins activated despite email failure
        updated = await tenant_service.get_tenant_by_id(setup["session"], tenant_id)
        assert set(updated.features.get("plugins", [])) == set(ENTERPRISE_PLUGINS)
