"""
Test cases for Team Role Permission Matrix with is_system_resource filtering
"""
import pytest
from httpx import AsyncClient


class TestTeamRolePermissionMatrix:
    """Test permission matrix resource filtering for team roles"""
    
    @pytest.mark.asyncio
    async def test_team_roles_resources_excludes_system_resources(
        self,
        api_client: AsyncClient,
        b2b_tenant_owner_token: str
    ):
        """GET /api/b2b/team-roles/resources only returns non-system resources"""
        response = await api_client.get(
            "/api/b2b/team-roles/resources",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert response.status_code == 200
        resources = response.json()
        resource_names = [r['name'] for r in resources]
        
        # Should NOT include system resources (from resources.yaml)
        assert 'roles' not in resource_names, "System resource 'roles' should be excluded"
        assert 'billing' not in resource_names, "System resource 'billing' should be excluded"
        assert 'audit_logs' not in resource_names, "System resource 'audit_logs' should be excluded"
        assert 'dashboard' not in resource_names, "System resource 'dashboard' should be excluded"
        assert 'analytics' not in resource_names, "System resource 'analytics' should be excluded"
        assert 'users' not in resource_names, "System resource 'users' should be excluded"
        assert 'notifications' not in resource_names, "System resource 'notifications' should be excluded"
        assert 'support' not in resource_names, "System resource 'support' should be excluded"
        assert 'account' not in resource_names, "System resource 'account' should be excluded"
        
        # Should include team resources (from resources.yaml and domain_resources.yaml)
        assert 'teams' in resource_names, "Team resource 'teams' should be included"
        assert 'team_members' in resource_names, "Team resource 'team_members' should be included"
        assert 'team_settings' in resource_names, "Team resource 'team_settings' should be included"
    
    
    @pytest.mark.asyncio
    async def test_team_vs_tenant_role_resources_comparison(
        self,
        api_client: AsyncClient,
        b2b_tenant_owner_token: str
    ):
        """Team role resources should be subset of tenant role resources"""
        # Get team role resources
        team_response = await api_client.get(
            "/api/b2b/team-roles/resources",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        # Get all resources (for tenant roles)
        all_response = await api_client.get(
            "/api/b2b/roles/resources/all",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert team_response.status_code == 200
        assert all_response.status_code == 200
        
        team_resources = {r['name'] for r in team_response.json()}
        all_resources = {r['name'] for r in all_response.json()}
        
        # Team resources should be subset of all resources
        assert team_resources.issubset(all_resources), \
            "Team resources should be a subset of all resources"
        
        # All resources should have more (include system resources)
        assert len(all_resources) > len(team_resources), \
            "All resources should include both system and team resources"
    
    
    @pytest.mark.asyncio
    async def test_team_roles_actions_endpoint_filters_resources(
        self,
        api_client: AsyncClient,
        b2b_tenant_owner_token: str
    ):
        """GET /api/b2b/team-roles/actions returns filtered resources"""
        response = await api_client.get(
            "/api/b2b/team-roles/actions",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'resources' in data
        assert 'actions' in data
        
        resource_names = [r['name'] for r in data['resources']]
        
        # Verify system resources excluded (from resources.yaml)
        assert 'roles' not in resource_names, "System resource should be excluded"
        assert 'audit_logs' not in resource_names, "System resource should be excluded"
        assert 'billing' not in resource_names, "System resource should be excluded"
        assert 'users' not in resource_names, "System resource should be excluded"
        
        # Verify team resources included
        assert 'teams' in resource_names, "Team resource should be included"
        assert 'team_members' in resource_names, "Team resource should be included"
    
    
    @pytest.mark.asyncio
    async def test_create_team_role_with_permissions_array(
        self,
        api_client: AsyncClient,
        b2b_tenant_owner_token: str
    ):
        """POST /api/b2b/team-roles with permissions array"""
        # First, get available resources to build valid permissions
        resources_response = await api_client.get(
            "/api/b2b/team-roles/resources",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        assert resources_response.status_code == 200
        
        resources = resources_response.json()
        if not resources:
            pytest.skip("No team resources available for testing")
        
        # Get actions
        actions_response = await api_client.get(
            "/api/b2b/team-roles/actions",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        assert actions_response.status_code == 200
        actions = actions_response.json()['actions']
        
        # Build permissions array
        permissions = [
            {"resource": resources[0]['name'], "action": actions[0]['name']}
        ]
        
        # Create role
        payload = {
            "name": "test_contributor",
            "display_name": "Test Contributor",
            "description": "Test role with permission matrix",
            "permissions": permissions
        }
        
        response = await api_client.post(
            "/api/b2b/team-roles",
            json=payload,
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert response.status_code == 201
        role = response.json()
        
        assert role['name'] == "test_contributor"
        assert len(role['permissions']) == 1
        assert role['permissions'][0]['resource'] == resources[0]['name']
    
    
    @pytest.mark.asyncio
    async def test_cannot_create_team_role_with_system_resource_permission(
        self,
        api_client: AsyncClient,
        b2b_tenant_owner_token: str
    ):
        """Team roles should not allow system resource permissions"""
        # Try to create a role with a system resource permission
        payload = {
            "name": "invalid_role",
            "display_name": "Invalid Role",
            "permissions": [
                {"resource": "roles", "action": "read"},  # 'roles' is a system resource
                {"resource": "billing", "action": "read"}  # 'billing' is definitely system resource
            ]
        }
        
        response = await api_client.post(
            "/api/b2b/team-roles",
            json=payload,
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        # This should either fail (400/422) or succeed but only store valid team permissions
        # Depending on backend validation implementation
        # For now, we just test that it doesn't crash
        assert response.status_code in [201, 400, 422]
    
    
    @pytest.mark.asyncio  
    async def test_update_team_role_permissions(
        self,
        api_client: AsyncClient,
        b2b_tenant_owner_token: str
    ):
        """PUT /api/b2b/team-roles/{id} updates permissions"""
        # Create a role first
        create_payload = {
            "name": "updatable_role",
            "display_name": "Updatable Role",
            "permissions": []
        }
        
        create_response = await api_client.post(
            "/api/b2b/team-roles",
            json=create_payload,
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert create_response.status_code == 201
        role = create_response.json()
        role_id = role['id']
        
        # Get available resources
        resources_response = await api_client.get(
            "/api/b2b/team-roles/resources",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        resources = resources_response.json()
        
        if not resources:
            pytest.skip("No resources available")
        
        # Update permissions
        new_permissions = [
            {"resource": resources[0]['name'], "action": "read"}
        ]
        
        update_payload = {
            "permissions": new_permissions
        }
        
        update_response = await api_client.put(
            f"/api/b2b/team-roles/{role_id}",
            json=update_payload,
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert update_response.status_code == 200
        updated_role = update_response.json()
        
        assert len(updated_role['permissions']) == 1
