"""
API Layer Tests: Plugin Middleware Enforcement

Tests the full stack of plugin enforcement at the API layer:
Request → Middleware → Plugin Registry → Plugin Logic → Response

TEST ORGANIZATION:
==================
1. TestTenantWithoutPlugins - Tests for tenants WITHOUT plugin features enabled
2. TestTenantWithPlugins - Tests for tenants WITH plugin features enabled
3. TestPluginMiddlewareFlow - Tests for the middleware execution flow itself
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy import select, text

from tests.conftest import (
    create_test_user,
    create_test_tenant,
    create_mock_firebase_token,
    encode_mock_jwt,
)

from modules.b2b.models.team import Team
from modules.b2b.models.team_member import TeamMember
from modules.b2b.models.team_role_definition import TeamRoleDefinition


pytestmark = pytest.mark.asyncio


# =============================================================================
# SCENARIO 1: TENANT WITHOUT PLUGINS (Standard RBAC Only)
# =============================================================================

class TestTenantWithoutPlugins:
    """
    Tests for tenants WITHOUT plugin features enabled.
    
    These tests verify that standard RBAC works correctly without any
    plugin interference. Plugins are NOT enabled, so:
    - No clearance level checks
    - No geographic boundary checks
    - No hierarchical team inheritance
    
    Only base RBAC (role permissions) should apply.
    """
    
    async def test_admin_can_list_teams_without_plugins(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [NO PLUGINS] Admin should access teams without plugin restrictions.
        
        Scenario: Standard tenant, no plugins enabled
        Expected: 200 OK - standard RBAC allows admin access
        """
        # Arrange - Default test setup has NO plugins enabled
        setup = b2b_test_setup
        token = setup["token"]
        
        # Act
        response = await api_client.get(
            "/api/b2b/teams/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert - Should be allowed by base RBAC
        assert response.status_code == 200
    
    async def test_admin_can_list_roles_without_plugins(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [NO PLUGINS] Admin should access roles without plugin restrictions.
        
        Scenario: Standard tenant, no plugins enabled
        Expected: 200 OK - standard RBAC allows admin access
        """
        # Arrange
        setup = b2b_test_setup
        token = setup["token"]
        
        # Act - Get role templates (admin can access)
        response = await api_client.get(
            "/api/b2b/roles/templates",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200
    
    async def test_viewer_denied_role_creation_without_plugins(
        self, api_client: AsyncClient, b2b_test_setup, db_session
    ):
        """
        [NO PLUGINS] Viewer should be denied role creation by base RBAC.
        
        Scenario: Standard tenant, no plugins enabled, viewer user
        Expected: 403 Forbidden - base RBAC denies viewer from creating roles
        """
        # Arrange - Create a viewer user
        setup = b2b_test_setup
        session = setup["session"]
        tenant = setup["tenant"]
        
        viewer = await create_test_user(
            session,
            tenant_id=tenant.id,
            email=f"viewer-{uuid4().hex[:6]}@{tenant.domain}",
            role_slug="viewer"
        )
        await session.commit()
        
        viewer_token = encode_mock_jwt(create_mock_firebase_token(
            uid=viewer.firebase_uid,
            email=viewer.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Act - Try to create a role (viewers cannot)
        response = await api_client.post(
            "/api/b2b/roles",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={
                "name": f"test_role_{uuid4().hex[:6]}",
                "display_name": "Test Role"
            }
        )
        
        # Assert - Should be 403 from base RBAC (not plugins)
        assert response.status_code == 403


# =============================================================================
# SCENARIO 2: TENANT WITH PLUGINS ENABLED
# =============================================================================

class TestTenantWithPlugins:
    """
    Tests for tenants WITH plugin features enabled.

    These tests verify that plugins correctly extend RBAC:
    - Data Classification: Clearance level vs sensitivity
    - Geographic Boundaries: User region vs resource region
    - Hierarchical Teams: Manager inheritance
    """

    async def test_auth_me_returns_plugin_enrichment_in_active_features(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [WITH PLUGINS] GET /auth/me must include plugin enrichment fields in active_features.

        Scenario: Tenant with all three plugins enabled
        Expected: active_features contains clearance_level, geographic_scopes,
                  accessible_teams, and context_enriched=True
        """
        setup = b2b_test_setup
        token = setup["token"]
        session = setup["session"]
        tenant_id = setup["tenant_id"]

        from modules.b2b.services.tenant_service import tenant_service
        await tenant_service.update_tenant_features(
            session, tenant_id,
            {"plugins": ["data_classification", "geographic_boundaries", "hierarchical_teams"]}
        )
        await session.commit()

        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        features = response.json().get("active_features", {})
        assert "clearance_level" in features, (
            "DataClassificationPlugin.enrich_user_context() not running"
        )
        assert "geographic_scopes" in features, (
            "GeographicBoundariesPlugin.enrich_user_context() not running"
        )
        assert "accessible_teams" in features, (
            "HierarchicalTeamsPlugin.enrich_user_context() not running"
        )
        assert features.get("context_enriched") is True

    @pytest.mark.skip(
        reason="Requires bank_surveillance alert endpoint with sensitivity field — "
               "add to test_plugin_integration.py once bank domain fixtures are seeded"
    )
    async def test_clearance_denies_access_to_higher_classification(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [WITH PLUGINS - DATA CLASSIFICATION]
        User with L1 clearance denied access to L3 resource.
        """

    @pytest.mark.skip(
        reason="Requires bank_surveillance alert endpoint with data_region_id field — "
               "add to test_plugin_integration.py once bank domain fixtures are seeded"
    )
    async def test_geographic_denies_access_to_different_region(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [WITH PLUGINS - GEOGRAPHIC BOUNDARIES]
        User with EU scope denied access to US-region alert.
        """

    async def test_hierarchical_grants_access_to_child_team(
        self, api_client: AsyncClient, b2b_test_setup, db_session
    ):
        """
        [WITH PLUGINS - HIERARCHICAL TEAMS]
        Manager of a parent team has child team in accessible_teams after enrichment.

        Scenario:
          - Parent team "APAC Region" → child team "SG Desk"
          - Admin user assigned to parent team with a role that has team_members:manage
          - hierarchical_teams plugin enabled
        Expected: active_features.accessible_teams includes both parent and child team IDs
        """
        setup = b2b_test_setup
        token = setup["token"]
        admin = setup["admin"]
        tenant_id = setup["tenant_id"]
        session = setup["session"]

        # Build team hierarchy directly in DB
        parent_team = Team(
            tenant_id=tenant_id,
            name=f"APAC-{uuid4().hex[:6]}",
            created_by=admin.id,
        )
        db_session.add(parent_team)
        await db_session.flush()

        child_team = Team(
            tenant_id=tenant_id,
            name=f"SG-Desk-{uuid4().hex[:6]}",
            created_by=admin.id,
            parent_team_id=parent_team.id,
        )
        db_session.add(child_team)
        await db_session.flush()

        manager_role = TeamRoleDefinition(
            tenant_id=tenant_id,
            name=f"manager_{uuid4().hex[:6]}",
            display_name="Test Manager",
            permissions=[{"resource": "team_members", "actions": ["manage"]}],
        )
        db_session.add(manager_role)
        await db_session.flush()

        membership = TeamMember(
            team_id=parent_team.id,
            user_id=admin.id,
            team_role_id=manager_role.id,
            team_role="team_manager",
        )
        db_session.add(membership)

        from modules.b2b.services.tenant_service import tenant_service
        await tenant_service.update_tenant_features(
            session, tenant_id, {"plugins": ["hierarchical_teams"]}
        )
        await db_session.commit()

        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        features = response.json().get("active_features", {})
        accessible = features.get("accessible_teams", [])

        assert str(parent_team.id) in accessible, "Parent team not in accessible_teams"
        assert str(child_team.id) in accessible, (
            "Child team not in accessible_teams — hierarchical plugin not expanding hierarchy"
        )


# =============================================================================
# SCENARIO 3: MIDDLEWARE FLOW TESTS
# =============================================================================

class TestPluginMiddlewareFlow:
    """
    Tests for the plugin middleware execution flow.
    
    These tests verify the middleware correctly handles:
    - Unauthenticated requests (401 before plugins run)
    - Plugin short-circuit behavior
    - Error propagation
    """
    
    async def test_unauthenticated_returns_401_not_plugin_error(
        self, api_client: AsyncClient
    ):
        """
        [MIDDLEWARE] Unauthenticated request should return 401, not plugin error.
        
        Scenario: No auth token provided
        Expected: 401 Unauthorized (auth middleware runs before plugins)
        """
        # Act - No auth header
        response = await api_client.get("/api/b2b/teams/")
        
        # Assert - Should be 401, not 403 from plugins
        assert response.status_code == 401
    
    async def test_expired_token_returns_401(
        self, api_client: AsyncClient
    ):
        """
        [MIDDLEWARE] Expired token should return 401.
        
        Scenario: Invalid/expired JWT token
        Expected: 401 Unauthorized (token validation before plugins)
        """
        # Act - Invalid token
        response = await api_client.get(
            "/api/b2b/teams/",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        # Assert
        assert response.status_code == 401
