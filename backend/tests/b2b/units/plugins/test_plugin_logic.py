"""
Unit Tests for RBAC Plugins Logic
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from types import SimpleNamespace
from core.rbac.plugin_system import PermissionContext
from plugins.data_classification.plugin import DataClassificationPlugin
from plugins.geographic_boundaries.plugin import GeographicBoundariesPlugin
from plugins.hierarchical_teams.plugin import HierarchicalTeamsPlugin

pytestmark = pytest.mark.asyncio

class MockResource:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class TestDataClassificationPlugin:
    
    async def test_deny_insufficient_clearance(self):
        plugin = DataClassificationPlugin()
        await plugin.initialize(None, {"default_level": "INTERNAL"})
        
        # Resource: Confidential (Level 2)
        resource = MockResource(sensitivity="CONFIDENTIAL")
        
        # User: Internal Clearance (Level 1)
        user_context = {"clearance_level": 1, "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        # Core result True (e.g. they have role access)
        # Plugin should VETO it
        result = await plugin.after_permission_check(ctx, True, None)
        assert result is False

    async def test_allow_sufficient_clearance(self):
        plugin = DataClassificationPlugin()
        await plugin.initialize(None, {"default_level": "INTERNAL"})
        
        # Resource: Confidential (Level 2)
        resource = MockResource(sensitivity="CONFIDENTIAL")
        
        # User: Confidential Clearance (Level 2)
        user_context = {"clearance_level": 2, "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await plugin.after_permission_check(ctx, True, None)
        assert result is True


class TestGeographicBoundariesPlugin:
    
    async def test_deny_wrong_region(self):
        plugin = GeographicBoundariesPlugin()
        await plugin.initialize(None, {"enforce_strict": True})
        
        # Resource: US Region
        us_uuid = "123e4567-e89b-12d3-a456-426614174000"
        resource = MockResource(data_region_id=us_uuid)
        
        # User: EU Scope only
        eu_uuid = "98765432-1234-5678-90ab-cdef12345678"
        user_context = {"geographic_scopes": [eu_uuid], "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await plugin.after_permission_check(ctx, True, None)
        assert result is False

    async def test_allow_matching_region(self):
        plugin = GeographicBoundariesPlugin()
        await plugin.initialize(None, {"enforce_strict": True})
        
        # Resource: US Region
        us_uuid = "123e4567-e89b-12d3-a456-426614174000"
        resource = MockResource(data_region_id=us_uuid)
        
        # User: US Scope
        user_context = {"geographic_scopes": [us_uuid], "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await plugin.after_permission_check(ctx, True, None)
        assert result is True
        
    async def test_bypass_global_role(self):
        plugin = GeographicBoundariesPlugin()
        # Config says 'admin' is global
        await plugin.initialize(None, {"enforce_strict": True, "global_roles": ["global_admin"]})
        
        # Resource: US Region
        us_uuid = "123e4567-e89b-12d3-a456-426614174000"
        resource = MockResource(data_region_id=us_uuid)
        
        # User: No scopes, but global_admin role
        user_context = {"geographic_scopes": [], "id": "u1", "role": "global_admin"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await plugin.after_permission_check(ctx, True, None)
        assert result is True


class TestHierarchicalTeamsPlugin:
    """Tests for HierarchicalTeamsPlugin - Database-Driven Permission Checks"""
    
    async def test_enrich_context_with_manage_permission(self):
        """
        [DATABASE-DRIVEN] User with team_members:manage permission gets child team access.
        
        This works with ANY role that has the permission, including:
        - team_manager (foundation)
        - regional_director (bank surveillance)
        - operations_manager (generic use case)
        """
        plugin = HierarchicalTeamsPlugin()
        await plugin.initialize(None, {})
        
        db = AsyncMock()
        
        # Mock: User has manage permission on Team A (True = has team_members:manage)
        plugin._get_direct_teams_with_permissions = AsyncMock(return_value={"team_A": True})
        
        # Mock _get_child_teams to return children B and C for Team A
        plugin._get_child_teams = AsyncMock(side_effect=lambda tid, db: ["team_B", "team_C"] if tid == "team_A" else [])
        
        user = {"id": "u1", "role": "member"}  # Not tenant admin, but has manage permission
        
        context_update = await plugin.enrich_user_context(user, db)
        
        teams = context_update.get("accessible_teams", [])
        assert "team_A" in teams
        assert "team_B" in teams
        assert "team_C" in teams
        assert len(teams) == 3

    async def test_non_manager_no_child_access(self):
        """
        [DATABASE-DRIVEN] User WITHOUT team_members:manage permission gets only direct teams.
        
        This applies to roles like:
        - team_contributor (foundation)
        - team_viewer (foundation)
        - surveillance_analyst (bank - read-only)
        """
        plugin = HierarchicalTeamsPlugin()
        await plugin.initialize(None, {})
        
        db = AsyncMock()
        
        # Mock: User does NOT have manage permission (False = no team_members:manage)
        plugin._get_direct_teams_with_permissions = AsyncMock(return_value={"team_A": False})
        plugin._get_child_teams = AsyncMock(return_value=["team_B", "team_C"])
        
        user = {"id": "u1", "role": "member"}
        
        context_update = await plugin.enrich_user_context(user, db)
        
        teams = context_update.get("accessible_teams", [])
        # Should only have direct team, NOT children
        assert "team_A" in teams
        assert "team_B" not in teams
        assert "team_C" not in teams
        assert len(teams) == 1
    
    async def test_tenant_admin_bypass(self):
        """
        [TENANT ADMIN] Tenant owner/admin gets child access regardless of team permissions.
        
        This is a system-level bypass that doesn't require any team role.
        """
        plugin = HierarchicalTeamsPlugin()
        await plugin.initialize(None, {})
        
        db = AsyncMock()
        
        # Mock: User is just a regular team member (no manage permission)
        plugin._get_direct_teams_with_permissions = AsyncMock(return_value={"team_A": False})
        plugin._get_child_teams = AsyncMock(return_value=["team_B", "team_C"])
        
        user = {"id": "u1", "role": "owner"}  # Tenant admin bypasses permission check
        
        context_update = await plugin.enrich_user_context(user, db)
        
        teams = context_update.get("accessible_teams", [])
        # Admin should get all teams including children
        assert "team_A" in teams
        assert "team_B" in teams
        assert "team_C" in teams


class TestDataClassificationPluginExtended:
    """Extended tests for DataClassificationPlugin edge cases"""
    
    async def test_default_level_applied_when_resource_has_no_sensitivity(self):
        """Test that default sensitivity level is used when resource has none"""
        plugin = DataClassificationPlugin()
        await plugin.initialize(None, {"default_level": "INTERNAL"})
        
        # Resource with NO sensitivity attribute
        resource = MockResource()  # No sensitivity
        
        # User: Internal Clearance (Level 1) - should match default INTERNAL
        user_context = {"clearance_level": 1, "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        # User with L1 clearance should pass for INTERNAL (L1) default
        result = await plugin.after_permission_check(ctx, True, None)
        assert result is True
    
    async def test_public_resource_allows_all_clearance_levels(self):
        """Test that PUBLIC resources allow even L0 clearance"""
        plugin = DataClassificationPlugin()
        await plugin.initialize(None, {"default_level": "INTERNAL"})
        
        # Resource: Public (Level 0)
        resource = MockResource(sensitivity="PUBLIC")
        
        # User: Lowest possible clearance
        user_context = {"clearance_level": 0, "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await plugin.after_permission_check(ctx, True, None)
        assert result is True
    
    async def test_top_secret_requires_highest_clearance(self):
        """Test that TOP_SECRET requires L4 clearance"""
        plugin = DataClassificationPlugin()
        await plugin.initialize(None, {"default_level": "INTERNAL"})
        
        # Resource: Top Secret (Level 4)
        resource = MockResource(sensitivity="TOP_SECRET")
        
        # User: Level 3 clearance - one below required
        user_context = {"clearance_level": 3, "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await plugin.after_permission_check(ctx, True, None)
        assert result is False
        
        # Now with L4 clearance
        user_context["clearance_level"] = 4
        result = await plugin.after_permission_check(ctx, True, None)
        assert result is True
    
    async def test_core_result_false_not_overridden(self):
        """Test that plugin doesn't grant access if core RBAC denied"""
        plugin = DataClassificationPlugin()
        await plugin.initialize(None, {"default_level": "INTERNAL"})
        
        # Resource: Public (should allow anyone)
        resource = MockResource(sensitivity="PUBLIC")
        
        # User: High clearance
        user_context = {"clearance_level": 4, "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        # Core RBAC said NO - plugin should respect that
        result = await plugin.after_permission_check(ctx, False, None)
        assert result is False


class TestGeographicBoundariesPluginExtended:
    """Extended tests for GeographicBoundariesPlugin edge cases"""
    
    async def test_no_region_on_resource_allows_access(self):
        """Test that resources without regions allow access"""
        plugin = GeographicBoundariesPlugin()
        await plugin.initialize(None, {"enforce_strict": True})
        
        # Resource: No data_region_id
        resource = MockResource()
        
        # User: EU Scope
        eu_uuid = "98765432-1234-5678-90ab-cdef12345678"
        user_context = {"geographic_scopes": [eu_uuid], "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await plugin.after_permission_check(ctx, True, None)
        assert result is True
    
    async def test_multiple_scopes_allows_if_any_match(self):
        """Test that user with multiple scopes passes if any match"""
        plugin = GeographicBoundariesPlugin()
        await plugin.initialize(None, {"enforce_strict": True})
        
        # Resource: US Region
        us_uuid = "123e4567-e89b-12d3-a456-426614174000"
        resource = MockResource(data_region_id=us_uuid)
        
        # User: Multiple scopes including US
        eu_uuid = "98765432-1234-5678-90ab-cdef12345678"
        user_context = {"geographic_scopes": [eu_uuid, us_uuid], "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await plugin.after_permission_check(ctx, True, None)
        assert result is True
    
    async def test_team_role_global_bypass(self):
        """Test that team-level global role bypasses geographic restrictions"""
        plugin = GeographicBoundariesPlugin()
        await plugin.initialize(None, {"enforce_strict": True, "global_roles": ["compliance_officer"]})
        
        # Resource: US Region
        us_uuid = "123e4567-e89b-12d3-a456-426614174000"
        resource = MockResource(data_region_id=us_uuid)
        
        # User: No geographic scopes, but has team-level global role
        user_context = {
            "geographic_scopes": [], 
            "id": "u1", 
            "role": "member",  # Not tenant-level bypass
            "team_roles": ["compliance_officer"]  # This is the bypass
        }
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await plugin.after_permission_check(ctx, True, None)
        assert result is True
    
    async def test_bypass_via_extra_context(self):
        """Test bypass via extra_context flag"""
        plugin = GeographicBoundariesPlugin()
        await plugin.initialize(None, {"enforce_strict": True})
        
        # Resource: US Region
        us_uuid = "123e4567-e89b-12d3-a456-426614174000"
        resource = MockResource(data_region_id=us_uuid)
        
        # User: No scopes at all
        user_context = {"geographic_scopes": [], "id": "u1"}
        
        ctx = PermissionContext(
            user_id=user_context["id"],
            user=user_context,
            resource_type="data",
            resource_id="r1",
            resource=resource,
            action="read",
            tenant_id="t1",
            extra_context={"bypass_geographic_restrictions": True}
        )

        result = await plugin.after_permission_check(ctx, True, None)
        assert result is True


# =============================================================================
# enrich_user_context — DataClassificationPlugin
# =============================================================================

class TestDataClassificationEnrich:
    """DataClassificationPlugin.enrich_user_context derives clearance from team roles."""

    async def test_returns_max_clearance_from_team_roles(self):
        plugin = DataClassificationPlugin()
        await plugin.initialize(None, {})

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3  # RESTRICTED
        db.execute.return_value = mock_result

        result = await plugin.enrich_user_context({"id": "u1"}, db)

        assert result["clearance_level"] == 3

    async def test_defaults_to_1_when_no_team_roles(self):
        """User with no team memberships defaults to INTERNAL (1)."""
        plugin = DataClassificationPlugin()
        await plugin.initialize(None, {})

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # no rows
        db.execute.return_value = mock_result

        result = await plugin.enrich_user_context({"id": "u1"}, db)

        assert result["clearance_level"] == 1

    async def test_defaults_to_1_when_no_user_id(self):
        """Missing user id must return clearance 1 without hitting DB."""
        plugin = DataClassificationPlugin()
        await plugin.initialize(None, {})

        result = await plugin.enrich_user_context({}, None)

        assert result["clearance_level"] == 1

    async def test_clearance_is_integer(self):
        plugin = DataClassificationPlugin()
        await plugin.initialize(None, {})

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 2
        db.execute.return_value = mock_result

        result = await plugin.enrich_user_context({"id": "u1"}, db)

        assert isinstance(result["clearance_level"], int)


# =============================================================================
# enrich_user_context — GeographicBoundariesPlugin
# =============================================================================

class TestGeographicBoundariesEnrich:
    """GeographicBoundariesPlugin.enrich_user_context derives scopes from accessible_teams."""

    async def test_no_accessible_teams_returns_empty(self):
        """When user has no accessible_teams, skip DB and return {} (fall back to DB column)."""
        plugin = GeographicBoundariesPlugin()
        plugin.config = {}

        result = await plugin.enrich_user_context(
            {"id": "u1", "accessible_teams": [], "geographic_scopes": []},
            None  # DB never called
        )

        assert result == {}

    async def test_derives_scopes_from_team_region_ids(self):
        """Accessible teams are mapped to their region_ids via DB query."""
        plugin = GeographicBoundariesPlugin()
        plugin.config = {}

        region_id = "123e4567-e89b-12d3-a456-426614174001"

        mock_row = MagicMock()
        mock_row.region_id = region_id

        db = AsyncMock()
        db.execute.return_value = [mock_row]  # iterable result

        result = await plugin.enrich_user_context(
            {"id": "u1", "accessible_teams": ["team_A"], "geographic_scopes": []},
            db
        )

        assert "geographic_scopes" in result
        assert region_id in result["geographic_scopes"]

    async def test_merges_with_existing_geographic_scopes(self):
        """Derived region IDs are merged with any pre-existing scopes on the user."""
        plugin = GeographicBoundariesPlugin()
        plugin.config = {}

        existing_scope = "aaaaaaaa-0000-0000-0000-000000000001"
        new_region = "bbbbbbbb-0000-0000-0000-000000000002"

        mock_row = MagicMock()
        mock_row.region_id = new_region

        db = AsyncMock()
        db.execute.return_value = [mock_row]

        result = await plugin.enrich_user_context(
            {"id": "u1", "accessible_teams": ["team_A"], "geographic_scopes": [existing_scope]},
            db
        )

        scopes = result["geographic_scopes"]
        assert existing_scope in scopes
        assert new_region in scopes

    async def test_teams_without_region_are_skipped(self):
        """Teams where region_id is NULL contribute no scope (not a crash)."""
        plugin = GeographicBoundariesPlugin()
        plugin.config = {}

        mock_row = MagicMock()
        mock_row.region_id = None  # team has no region

        db = AsyncMock()
        db.execute.return_value = [mock_row]

        result = await plugin.enrich_user_context(
            {"id": "u1", "accessible_teams": ["team_A"], "geographic_scopes": []},
            db
        )

        # None region filtered out; no scopes derived → fall back, return {}
        assert result == {}


# =============================================================================
# check_dependencies — GeographicBoundariesPlugin
# =============================================================================

class TestGeographicCheckDependencies:
    """Geographic plugin warns when hierarchical_teams is absent."""

    def test_warns_when_hierarchical_teams_absent(self):
        plugin = GeographicBoundariesPlugin()
        plugin.config = {}

        with patch("plugins.geographic_boundaries.plugin.logger") as mock_logger:
            plugin.check_dependencies(["data_classification"])
            mock_logger.warning.assert_called_once()
            warning_text = mock_logger.warning.call_args[0][0]
            assert "hierarchical_teams" in warning_text

    def test_no_warning_when_hierarchical_teams_present(self):
        plugin = GeographicBoundariesPlugin()
        plugin.config = {}

        with patch("plugins.geographic_boundaries.plugin.logger") as mock_logger:
            plugin.check_dependencies(["hierarchical_teams", "data_classification"])
            mock_logger.warning.assert_not_called()
