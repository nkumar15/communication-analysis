"""
Unit Tests for RBAC Plugins Logic
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
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
    
    async def test_enrich_context_recursion(self):
        plugin = HierarchicalTeamsPlugin()
        await plugin.initialize(None, {})
        
        # Mocks
        db = AsyncMock()
        
        # Mock _get_direct_teams_with_roles to return User manages Team A
        # Use a role contained in the hardcoded list: "regional_director"
        plugin._get_direct_teams_with_roles = AsyncMock(return_value={"team_A": "regional_director"})
        
        # Mock _get_child_teams to return children B and C for Team A
        plugin._get_child_teams = AsyncMock(side_effect=lambda tid, db: ["team_B", "team_C"] if tid == "team_A" else [])
        
        user = {"id": "u1", "role": "member"} # Not tenant admin, but manager of Team A
        
        context_update = await plugin.enrich_user_context(user, db)
        
        teams = context_update.get("accessible_teams", [])
        assert "team_A" in teams
        assert "team_B" in teams
        assert "team_C" in teams
        assert len(teams) == 3
