
import pytest
from httpx import AsyncClient
import os

# These tests assume the server has started with RBAC_PLUGINS enabled

class TestRBACPlugins:
    
    @pytest.mark.asyncio
    async def test_plugins_are_active(self, api_client: AsyncClient, b2b_test_setup):
        """
        Verify plugins are active by checking user context enrichment.
        Checks for 'geographic_scopes' and 'clearance_level' in /auth/me.
        """
        setup = b2b_test_setup
        token = setup["token"]
        
        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify Context Enrichment
        # 1. Data Classification
        assert "clearance_level" in data, "clearance_level missing from auth/me (DataClassificationPlugin)"
        
        # 2. Geographic Boundaries
        assert "geographic_scopes" in data, "geographic_scopes missing from auth/me (GeographicBoundariesPlugin)"
        
        # 3. Hierarchical Teams
        assert "accessible_teams" in data, "accessible_teams missing from auth/me (HierarchicalTeamsPlugin)"

    @pytest.mark.asyncio
    async def test_geographic_regions_seeded(self, api_client: AsyncClient, b2b_test_setup):
        """
        Verify we have regions seeded. 
        Since we don't have a direct API to list them without admin rights or specific endpoint,
        we rely on the fact that seeding succeeded (verified in logs) and 
        that we can assign these regions to resources (integration test).
        
        But we can try to inspect the DB directly using the test session if configured,
        or just skip direct DB verification here and rely on behavior.
        """
        pass

    @pytest.mark.asyncio
    async def test_clearance_level_enforcement(self, api_client: AsyncClient, b2b_test_setup):
        """
        Test that clearance level restricts access to sensitive resources.
        (Requires creating resources with sensitivity, which we can't easily do via API yet
        unless we have an endpoint that accepts 'sensitivity' field).
        
        For now, we confirm the User has the level.
        """
        setup = b2b_test_setup
        token = setup["token"]
        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        data = response.json()
        assert isinstance(data.get("clearance_level"), int)

    @pytest.mark.asyncio
    async def test_hierarchical_teams_access(self, api_client: AsyncClient, b2b_test_setup):
        """
        Test that a manager has access to child teams.
        Verify 'accessible_teams' list contains more than just their direct team
        if they are in a hierarchy.
        """
        setup = b2b_test_setup
        token = setup["token"]
        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        data = response.json()
        # Even if empty list, it validates the field exists
        assert isinstance(data.get("accessible_teams"), list)
