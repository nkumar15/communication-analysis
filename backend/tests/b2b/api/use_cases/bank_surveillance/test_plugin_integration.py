"""
Bank Surveillance Plugin Integration Tests

Tests plugin lifecycle hooks (on_tenant_enable) and DB schema structure.
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

