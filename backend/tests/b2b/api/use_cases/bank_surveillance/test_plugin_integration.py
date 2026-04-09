"""
Bank Surveillance Plugin Integration Tests

Tests plugin lifecycle hooks (on_tenant_enable) and DB schema structure.
Subscription-upgrade / downgrade tests use a mocked SubscriptionService provider
(no real Stripe calls) — same pattern as test_subscription_checkout.py.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from sqlalchemy import text, select

pytestmark = pytest.mark.asyncio


# =============================================================================
# Helpers
# =============================================================================

async def enable_plugins_for_tenant(session, tenant_id, plugins: list[str]):
    """Enable plugins for a tenant (simulates subscription upgrade)."""
    from sqlalchemy.orm.attributes import flag_modified
    from modules.b2b.services.tenant_service import tenant_service

    await tenant_service.update_tenant_features(
        session, tenant_id, {"plugins": plugins}
    )
    await session.commit()


def _mock_db_with_template(template_data: dict):
    """
    Build an AsyncMock DB whose first execute() call returns a template,
    and all subsequent calls return None (no existing records).
    """
    call_count = {"n": 0}

    mock_template = MagicMock()
    mock_template.template_data = template_data

    async def mock_execute(stmt, *args, **kwargs):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.scalar_one_or_none.return_value = mock_template
        else:
            result.scalar_one_or_none.return_value = None
        return result

    db = AsyncMock()
    db.execute.side_effect = mock_execute
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _mock_db_no_template():
    """DB that returns no template — hooks should log warning and return cleanly."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


# =============================================================================
# Schema Smoke Test
# =============================================================================

async def test_plugin_schema_isolation(db_session, b2b_test_setup):
    """
    Verify the b2b schema exists.
    This is a smoke test that does not require plugin-specific seeding.
    """
    result = await db_session.execute(text("""
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name IN ('b2b', 'bank_surveillance')
    """))
    schemas = [row[0] for row in result.fetchall()]

    assert 'b2b' in schemas, "b2b schema must exist"


# =============================================================================
# GeographicBoundariesPlugin — lifecycle hook
# =============================================================================

async def test_geographic_boundaries_on_tenant_enable_with_template():
    """
    on_tenant_enable clones default_regions from PluginTemplate into GeographicRegion.
    Each region is inserted once (idempotent — skips if already exists).
    """
    from plugins.geographic_boundaries.plugin import GeographicBoundariesPlugin

    plugin = GeographicBoundariesPlugin()
    plugin.config = {}
    tenant_id = str(uuid4())

    db = _mock_db_with_template({
        "default_regions": [
            {"code": "US", "name": "United States", "regulatory_jurisdiction": "Federal"},
            {"code": "EU", "name": "Europe", "regulatory_jurisdiction": "GDPR"},
        ]
    })

    # Must not raise
    await plugin.on_tenant_enable(tenant_id, db)

    # Two regions → two db.add() calls
    assert db.add.call_count == 2
    db.flush.assert_called_once()


async def test_geographic_boundaries_on_tenant_enable_no_template():
    """
    on_tenant_enable logs a warning and exits cleanly when no template is found.
    No DB inserts must happen.
    """
    from plugins.geographic_boundaries.plugin import GeographicBoundariesPlugin

    plugin = GeographicBoundariesPlugin()
    plugin.config = {}

    db = _mock_db_no_template()

    await plugin.on_tenant_enable(str(uuid4()), db)

    db.add.assert_not_called()


async def test_geographic_boundaries_on_tenant_disable_is_noop():
    """on_tenant_disable must complete without errors and never delete data."""
    from plugins.geographic_boundaries.plugin import GeographicBoundariesPlugin

    plugin = GeographicBoundariesPlugin()
    plugin.config = {}
    db = AsyncMock()

    await plugin.on_tenant_disable(str(uuid4()), db)

    db.delete.assert_not_called()
    db.execute.assert_not_called()


# =============================================================================
# DataClassificationPlugin — lifecycle hook
# =============================================================================

async def test_data_classification_on_tenant_enable_with_template():
    """
    on_tenant_enable clones sensitivity_levels from PluginTemplate into SensitivityLevel.
    """
    from plugins.data_classification.plugin import DataClassificationPlugin

    plugin = DataClassificationPlugin()
    await plugin.initialize(None, {})
    tenant_id = str(uuid4())

    db = _mock_db_with_template({
        "sensitivity_levels": [
            {"name": "PUBLIC", "level": 0, "description": "Public data"},
            {"name": "INTERNAL", "level": 1, "description": "Internal use only"},
            {"name": "CONFIDENTIAL", "level": 2, "description": "Confidential"},
        ]
    })

    await plugin.on_tenant_enable(tenant_id, db)

    # Three levels → three db.add() calls
    assert db.add.call_count == 3
    db.flush.assert_called_once()


async def test_data_classification_on_tenant_enable_no_template():
    """on_tenant_enable exits cleanly when no template is found."""
    from plugins.data_classification.plugin import DataClassificationPlugin

    plugin = DataClassificationPlugin()
    await plugin.initialize(None, {})

    db = _mock_db_no_template()

    await plugin.on_tenant_enable(str(uuid4()), db)

    db.add.assert_not_called()


async def test_data_classification_on_tenant_disable_is_noop():
    """on_tenant_disable must complete without deleting data."""
    from plugins.data_classification.plugin import DataClassificationPlugin

    plugin = DataClassificationPlugin()
    await plugin.initialize(None, {})
    db = AsyncMock()

    await plugin.on_tenant_disable(str(uuid4()), db)

    db.delete.assert_not_called()
    db.execute.assert_not_called()


# =============================================================================
# HierarchicalTeamsPlugin — lifecycle hook
# =============================================================================

async def test_hierarchical_teams_on_tenant_enable_with_template():
    """
    on_tenant_enable clones org_tiers from PluginTemplate into OrgTier.
    """
    from plugins.hierarchical_teams.plugin import HierarchicalTeamsPlugin

    plugin = HierarchicalTeamsPlugin()
    await plugin.initialize(None, {})
    tenant_id = str(uuid4())

    db = _mock_db_with_template({
        "org_tiers": [
            {"name": "GLOBAL", "display_name": "Global", "hierarchy_order": 1},
            {"name": "REGIONAL", "display_name": "Regional", "hierarchy_order": 2},
            {"name": "COUNTRY", "display_name": "Country", "hierarchy_order": 3},
            {"name": "DESK", "display_name": "Desk", "hierarchy_order": 4},
        ]
    })

    await plugin.on_tenant_enable(tenant_id, db)

    # Four tiers → four db.add() calls
    assert db.add.call_count == 4
    db.flush.assert_called_once()


async def test_hierarchical_teams_on_tenant_enable_no_template():
    """on_tenant_enable exits cleanly when no template is found."""
    from plugins.hierarchical_teams.plugin import HierarchicalTeamsPlugin

    plugin = HierarchicalTeamsPlugin()
    await plugin.initialize(None, {})

    db = _mock_db_no_template()

    await plugin.on_tenant_enable(str(uuid4()), db)

    db.add.assert_not_called()


async def test_hierarchical_teams_on_tenant_disable_is_noop():
    """on_tenant_disable must complete without deleting data."""
    from plugins.hierarchical_teams.plugin import HierarchicalTeamsPlugin

    plugin = HierarchicalTeamsPlugin()
    await plugin.initialize(None, {})
    db = AsyncMock()

    await plugin.on_tenant_disable(str(uuid4()), db)

    db.delete.assert_not_called()
    db.execute.assert_not_called()


# =============================================================================
# Subscription upgrade / downgrade — mocked Stripe provider
# =============================================================================

BANK_PLUGINS = ["geographic_boundaries", "hierarchical_teams", "data_classification"]


def _make_checkout_session(tenant_id: str, tier: str, seats: int = 5) -> dict:
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
    from modules.b2b.models import B2BSubscriptionPlan
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


async def _seed_plan(db_session):
    from modules.b2b.models import B2BSubscriptionPlan
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


async def _build_service(db_session, mock_plan: MagicMock):
    from modules.b2b.services.subscription_service import SubscriptionService
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


async def test_subscription_upgrade_enables_all_bank_plugins(
    db_session, b2b_test_setup
):
    """
    Stripe checkout for enterprise tier must enable all 3 bank plugins on the tenant
    and call each plugin's on_tenant_enable hook exactly once.
    Uses mocked Stripe provider — no real Stripe calls.
    """
    from modules.b2b.services.tenant_service import tenant_service

    setup = b2b_test_setup
    tenant_id = setup["tenant_id"]
    real_plan = await _seed_plan(db_session)

    # Tenant starts with no plugins
    await tenant_service.update_tenant_features(db_session, tenant_id, {"plugins": []})
    await db_session.commit()

    mock_plan = _mock_plan("enterprise", BANK_PLUGINS, real_plan.id)
    svc = await _build_service(db_session, mock_plan)
    session_data = _make_checkout_session(str(tenant_id), tier="enterprise")

    hook_calls: list[str] = []

    # Each side_effect must be a proper async callable so that
    # `await plugin.on_tenant_enable(t, d)` in the service resolves correctly.
    async def spy_geo_enable(t_id: str, db):
        hook_calls.append("geographic_boundaries")

    async def spy_hierarchical_enable(t_id: str, db):
        hook_calls.append("hierarchical_teams")

    async def spy_data_class_enable(t_id: str, db):
        hook_calls.append("data_classification")

    with (
        patch("infrastructure.email.email_service.send_subscription_confirmation_email"),
        patch(
            "plugins.geographic_boundaries.plugin.GeographicBoundariesPlugin.on_tenant_enable",
            side_effect=spy_geo_enable,
        ),
        patch(
            "plugins.hierarchical_teams.plugin.HierarchicalTeamsPlugin.on_tenant_enable",
            side_effect=spy_hierarchical_enable,
        ),
        patch(
            "plugins.data_classification.plugin.DataClassificationPlugin.on_tenant_enable",
            side_effect=spy_data_class_enable,
        ),
    ):
        await svc.handle_checkout_completed(session_data)
        await db_session.commit()

    # All 3 bank plugins must be active in tenant features
    updated = await tenant_service.get_tenant_by_id(setup["session"], tenant_id)
    active_plugins = set(updated.features.get("plugins", []))
    assert active_plugins == set(BANK_PLUGINS), (
        f"Expected {BANK_PLUGINS}, got {sorted(active_plugins)}"
    )

    # Each plugin's on_tenant_enable hook called exactly once
    assert set(hook_calls) == set(BANK_PLUGINS), (
        f"Hook calls: {hook_calls}"
    )
    assert len(hook_calls) == 3


async def test_subscription_downgrade_removes_bank_plugins(
    db_session, b2b_test_setup
):
    """
    Stripe checkout for starter tier after enterprise must remove all 3 bank plugins.
    Existing plugin data in DB must NOT be deleted (safe downgrade — data preserved).
    on_tenant_disable must be called for each removed plugin.
    """
    from modules.b2b.services.tenant_service import tenant_service

    setup = b2b_test_setup
    tenant_id = setup["tenant_id"]
    real_plan = await _seed_plan(db_session)

    # Tenant starts on enterprise with all bank plugins active
    await tenant_service.update_tenant_features(
        db_session, tenant_id, {"plugins": BANK_PLUGINS, "sso": True}
    )
    await db_session.commit()

    mock_starter = _mock_plan("starter", [], real_plan.id)
    svc = await _build_service(db_session, mock_starter)
    session_data = _make_checkout_session(str(tenant_id), tier="starter")

    disable_calls: list[str] = []

    async def spy_geo_disable(t_id: str, db):
        disable_calls.append("geographic_boundaries")

    async def spy_hierarchical_disable(t_id: str, db):
        disable_calls.append("hierarchical_teams")

    async def spy_data_class_disable(t_id: str, db):
        disable_calls.append("data_classification")

    with (
        patch("infrastructure.email.email_service.send_subscription_confirmation_email"),
        patch(
            "plugins.geographic_boundaries.plugin.GeographicBoundariesPlugin.on_tenant_disable",
            side_effect=spy_geo_disable,
        ),
        patch(
            "plugins.hierarchical_teams.plugin.HierarchicalTeamsPlugin.on_tenant_disable",
            side_effect=spy_hierarchical_disable,
        ),
        patch(
            "plugins.data_classification.plugin.DataClassificationPlugin.on_tenant_disable",
            side_effect=spy_data_class_disable,
        ),
    ):
        await svc.handle_checkout_completed(session_data)
        await db_session.commit()

    # Plugins must be cleared from tenant features after downgrade
    updated = await tenant_service.get_tenant_by_id(setup["session"], tenant_id)
    assert updated.features.get("plugins", []) == [], (
        f"Expected empty plugins after downgrade, got {updated.features.get('plugins')}"
    )
    assert updated.features.get("sso") is False

    # on_tenant_disable called for each removed plugin
    assert set(disable_calls) == set(BANK_PLUGINS), (
        f"Disable hook calls: {disable_calls}"
    )
    assert len(disable_calls) == 3
