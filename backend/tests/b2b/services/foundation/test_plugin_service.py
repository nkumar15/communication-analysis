"""
Service Layer Tests: Plugin Service Integration

Tests plugins with real database interactions including:
- Plugin lifecycle (enable/disable hooks)
- Data Classification enforcement with DB
- Geographic Boundaries enforcement with DB
- Hierarchical Teams access with DB
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy import select, text
from unittest.mock import AsyncMock, patch

from plugins.data_classification.plugin import DataClassificationPlugin
from plugins.geographic_boundaries.plugin import GeographicBoundariesPlugin
from plugins.hierarchical_teams.plugin import HierarchicalTeamsPlugin
from core.rbac.plugin_system import PermissionContext


pytestmark = pytest.mark.asyncio


class MockResource:
    """Mock resource for plugin testing"""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestDataClassificationServiceIntegration:
    """Tests for DataClassificationPlugin with real DB session"""
    
    async def test_enrich_user_context_fetches_clearance_from_db(self, db_session, b2b_test_setup):
        """Test that enrich_user_context fetches clearance level from role in DB"""
        # Arrange
        setup = b2b_test_setup
        session = setup["session"]
        owner = setup["owner"]
        
        plugin = DataClassificationPlugin()
        await plugin.initialize(session, {"default_level": "INTERNAL"})
        
        # User context with role_id
        user = {
            "id": str(owner.id),
            "role_id": str(owner.role_id) if owner.role_id else None
        }
        
        # Act
        enriched = await plugin.enrich_user_context(user, session)
        
        # Assert
        assert "clearance_level" in enriched
        assert isinstance(enriched["clearance_level"], int)


class TestGeographicBoundariesServiceIntegration:
    """Tests for GeographicBoundariesPlugin with real DB session"""
    
    async def test_enrich_user_context_fetches_scopes_from_db(self, db_session, b2b_test_setup):
        """Test that enrich_user_context fetches geographic scopes from team memberships"""
        # Arrange
        setup = b2b_test_setup
        session = setup["session"]
        owner = setup["owner"]
        tenant_id = setup["tenant_id"]
        
        plugin = GeographicBoundariesPlugin()
        await plugin.initialize(session, {"enforce_strict": True})
        
        user = {
            "id": str(owner.id),
            "tenant_id": str(tenant_id)
        }
        
        # Act
        enriched = await plugin.enrich_user_context(user, session)
        
        # Assert
        assert "geographic_scopes" in enriched
        assert isinstance(enriched["geographic_scopes"], list)
        # team_roles may also be present
        assert "team_roles" in enriched


class TestHierarchicalTeamsServiceIntegration:
    """Tests for HierarchicalTeamsPlugin with real DB session"""
    
    async def test_enrich_user_context_fetches_accessible_teams(self, db_session, b2b_test_setup):
        """Test that enrich_user_context fetches accessible teams from DB"""
        # Arrange
        setup = b2b_test_setup
        session = setup["session"]
        owner = setup["owner"]
        
        plugin = HierarchicalTeamsPlugin()
        await plugin.initialize(session, {})
        
        user = {
            "id": str(owner.id),
            "role": "admin"  # Tenant admin
        }
        
        # Act
        enriched = await plugin.enrich_user_context(user, session)
        
        # Assert
        assert "accessible_teams" in enriched
        assert isinstance(enriched["accessible_teams"], list)


class TestPluginLifecycle:
    """Tests for plugin enable/disable lifecycle hooks"""
    
    @pytest.mark.xfail(reason="Plugin templates may not be seeded in test environment")
    async def test_data_classification_enable_creates_sensitivity_levels(self, db_session, b2b_test_setup):
        """Test that enabling data_classification plugin creates sensitivity levels"""
        # Arrange
        setup = b2b_test_setup
        session = setup["session"]
        tenant_id = setup["tenant_id"]
        
        plugin = DataClassificationPlugin()
        await plugin.initialize(session, {"default_level": "INTERNAL"})
        
        # Act
        await plugin.on_tenant_enable(str(tenant_id), session)
        await session.commit()
        
        # Assert - check for created sensitivity levels
        result = await session.execute(
            text("SELECT COUNT(*) FROM b2b.sensitivity_levels WHERE tenant_id = :tid"),
            {"tid": tenant_id}
        )
        count = result.scalar()
        
        # Should have created some default levels
        assert count > 0
    
    @pytest.mark.xfail(reason="Plugin templates may not be seeded in test environment")
    async def test_geographic_boundaries_enable_creates_regions(self, db_session, b2b_test_setup):
        """Test that enabling geographic_boundaries plugin creates default regions"""
        # Arrange
        setup = b2b_test_setup
        session = setup["session"]
        tenant_id = setup["tenant_id"]
        
        plugin = GeographicBoundariesPlugin()
        await plugin.initialize(session, {"enforce_strict": True})
        
        # Act
        await plugin.on_tenant_enable(str(tenant_id), session)
        await session.commit()
        
        # Assert - check for created regions
        result = await session.execute(
            text("SELECT COUNT(*) FROM b2b.geographic_regions WHERE tenant_id = :tid"),
            {"tid": tenant_id}
        )
        count = result.scalar()
        
        # Should have created some default regions
        assert count > 0


class TestPluginEnforcementWithDB:
    """Tests for plugin permission enforcement with real DB resources"""
    
    async def test_clearance_enforcement_with_db_context(self, db_session, b2b_test_setup):
        """Test data classification enforcement with DB-enriched user context"""
        # Arrange
        setup = b2b_test_setup
        session = setup["session"]
        
        plugin = DataClassificationPlugin()
        await plugin.initialize(session, {"default_level": "INTERNAL"})
        
        # Resource: Confidential (Level 2)
        resource = MockResource(sensitivity="CONFIDENTIAL")
        
        # User with low clearance
        user_context = {"clearance_level": 1, "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id=str(setup["tenant_id"]),
            extra_context={}
        )
        
        # Act - Core allowed, plugin should deny
        result = await plugin.after_permission_check(ctx, True, session)
        
        # Assert
        assert result is False
    
    async def test_geographic_enforcement_with_db_context(self, db_session, b2b_test_setup):
        """Test geographic boundaries enforcement with DB-enriched user context"""
        # Arrange
        setup = b2b_test_setup
        session = setup["session"]
        
        plugin = GeographicBoundariesPlugin()
        await plugin.initialize(session, {"enforce_strict": True})
        
        # Resource with a region ID
        us_uuid = str(uuid4())
        resource = MockResource(data_region_id=us_uuid)
        
        # User with different region scope
        eu_uuid = str(uuid4())
        user_context = {"geographic_scopes": [eu_uuid], "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id=str(setup["tenant_id"]),
            extra_context={}
        )
        
        # Act - Core allowed, plugin should deny (wrong region)
        result = await plugin.after_permission_check(ctx, True, session)
        
        # Assert
        assert result is False
