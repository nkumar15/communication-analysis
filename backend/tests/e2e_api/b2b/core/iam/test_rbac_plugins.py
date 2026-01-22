
import pytest
from httpx import AsyncClient
import os

# These tests require:
# 1. Plugin registration in the test app lifespan
# 2. Tenant subscription with plugins enabled
# 3. DB infrastructure (clearance_level column, geographic_regions table, parent_team_id)
# 4. Seeded plugin-specific data
#
# Currently, plugin logic is tested via unit tests in tests/units/plugins/test_plugin_logic.py
# These E2E tests are skipped until production code integrates plugin enrichment in /auth/me

@pytest.mark.integration
class TestRBACPlugins:
    
    @pytest.mark.asyncio
    async def test_plugins_are_active(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """
        Verify plugins are active by checking user context enrichment.
        Checks for 'geographic_scopes' and 'clearance_level' in /auth/me within active_features.
        """
        # Arrange
        setup = b2b_test_setup
        token = setup["token"]
        session = setup['session']
        tenant_id = setup['tenant_id']
        
        # Manually enable plugins for this test tenant
        from modules.b2b.services.tenant_service import tenant_service
        
        # Enable all plugins relevant for RBAC
        await tenant_service.update_tenant_features(
            session, 
            tenant_id, 
            {
                "plugins": [
                    "data_classification", 
                    "geographic_boundaries", 
                    "hierarchical_teams"
                ]
            }
        )
        await session.commit()
        
        # Act
        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        active_features = data.get("active_features", {})
        
        # Verify Context Enrichment
        # 1. Data Classification
        assert "clearance_level" in active_features, "clearance_level missing from active_features (DataClassificationPlugin)"
        
        # 2. Geographic Boundaries
        assert "geographic_scopes" in active_features, "geographic_scopes missing from active_features (GeographicBoundariesPlugin)"
        
        # 3. Hierarchical Teams
        assert "accessible_teams" in active_features, "accessible_teams missing from active_features (HierarchicalTeamsPlugin)"

    @pytest.mark.asyncio
    async def test_clearance_level_from_role(self, api_client: AsyncClient, b2b_test_setup):
        """
        Test that clearance level matches the user's role configuration.
        """
        # Arrange
        setup = b2b_test_setup
        token = setup["token"]
        # Default 'admin' role should have clearance level 4 (most restricted) or similar depending on setup
        
        # Act
        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        active_features = data.get("active_features", {})
        assert "clearance_level" in active_features
        assert isinstance(active_features["clearance_level"], int)

    @pytest.mark.asyncio
    async def test_geographic_scopes_initialization(self, api_client: AsyncClient, b2b_test_setup):
        """
        Test that geographic scopes are initialized as an empty list (or populated) upon enablement.
        """
        # Arrange
        setup = b2b_test_setup
        token = setup["token"]
        
        # Act
        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        active_features = data.get("active_features", {})
        # Geographic scopes should be a list (likely empty if no regions assigned to teams yet)
        assert isinstance(active_features.get("geographic_scopes"), list)
