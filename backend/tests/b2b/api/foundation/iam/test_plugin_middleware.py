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
    
    Note: Many of these tests require specific infrastructure:
    - Plugin enrichment in auth_service (pending integration)
    - Domain resources with sensitivity/region fields (bank_surveillance)
    """
    
    @pytest.mark.xfail(reason="Plugin enrichment in auth_service pending re-integration")
    async def test_auth_me_returns_plugin_context(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [WITH PLUGINS] GET /auth/me should return plugin-enriched context.
        
        Scenario: Tenant with plugins enabled
        Expected: Response includes clearance_level, geographic_scopes, accessible_teams
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
        
        # Check for plugin enrichment in response
        assert "active_features" in data or "user" in data
        if "active_features" in data:
            features = data["active_features"]
            assert "clearance_level" in features
            assert "geographic_scopes" in features
            assert "accessible_teams" in features
    
    @pytest.mark.xfail(reason="Requires bank_surveillance domain resources")
    async def test_clearance_denies_access_to_higher_classification(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [WITH PLUGINS - DATA CLASSIFICATION]
        User with L1 clearance should be denied access to L3 resource.
        
        Scenario: Tenant with data_classification plugin enabled
        Expected: 403 Forbidden - plugin denies due to insufficient clearance
        """
        # This test requires:
        # 1. A resource endpoint with sensitivity field (bank_surveillance)
        # 2. Plugin middleware active and integrated with auth_service
        pytest.skip("Requires bank_surveillance domain with classified resources")
    
    @pytest.mark.xfail(reason="Requires bank_surveillance domain resources")
    async def test_geographic_denies_access_to_different_region(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [WITH PLUGINS - GEOGRAPHIC BOUNDARIES]
        User in EU should be denied access to US-region resource.
        
        Scenario: Tenant with geographic_boundaries plugin enabled
        Expected: 403 Forbidden - plugin denies due to region mismatch
        """
        # This test requires:
        # 1. A resource endpoint with data_region_id field (bank_surveillance)
        # 2. Plugin middleware active and integrated with auth_service
        pytest.skip("Requires bank_surveillance domain with region-tagged resources")
    
    @pytest.mark.xfail(reason="Requires team hierarchy seeded in test")
    async def test_hierarchical_grants_access_to_child_team(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [WITH PLUGINS - HIERARCHICAL TEAMS]
        Manager of parent team should access child team resources.
        
        Scenario: Tenant with hierarchical_teams plugin enabled
        Expected: 200 OK - plugin grants access due to hierarchy inheritance
        """
        # This test requires:
        # 1. Parent-child team hierarchy seeded
        # 2. User assigned as manager of parent team
        # 3. Plugin enrichment to add accessible_teams
        pytest.skip("Requires hierarchical team structure in test fixture")


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
