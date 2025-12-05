"""
Integration tests for Projects API

Tests cover:
- CRUD operations
- Team-scoped access control
- Multi-tenant isolation
- Owner/Admin bypass
"""
import pytest
from uuid import uuid4


class TestProjectsAPI:
    """Test suite for Projects endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_project(self, api_client, domain_test_data):
        """Test creating a project"""
        response = await api_client.post(
            "/api/b2b/projects",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "team_id": str(domain_test_data['default_team'].id),
                "name": "Test Project",
                "description": "A test project"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["team_id"] == str(domain_test_data['default_team'].id)
        assert data["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_create_project_nonexistent_team(self, api_client, domain_test_data):
        """Test project creation with non-existent team fails"""
        response = await api_client.post(
            "/api/b2b/projects",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "team_id": str(uuid4()),
                "name": "Test Project",
                "description": "Should fail"
            }
        )
        assert response.status_code in [403, 404]
    
    @pytest.mark.asyncio
    async def test_list_projects_team_scoped(
        self, 
        api_client, 
        domain_test_data,
        team_project,
        other_team_project
    ):
        """Test listing projects returns only user's team projects"""
        response = await api_client.get(
            "/api/b2b/projects",
            headers={"Authorization": f"Bearer {domain_test_data['team_member_token']}"}
        )
        assert response.status_code == 200
        projects = response.json()
        project_ids = [p["id"] for p in projects]
        assert str(team_project) in project_ids
        assert str(other_team_project) not in project_ids
    
    @pytest.mark.asyncio
    async def test_owner_sees_all_projects(
        self,
        api_client,
        domain_test_data,
        team_project,
        other_team_project
    ):
        """Test owner can see all projects in tenant"""
        response = await api_client.get(
            "/api/b2b/projects",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 200
        projects = response.json()
        project_ids = [p["id"] for p in projects]
        assert str(team_project) in project_ids
        assert str(other_team_project) in project_ids
    
    @pytest.mark.asyncio
    async def test_get_project(self, api_client, domain_test_data, team_project):
        """Test getting specific project"""
        response = await api_client.get(
            f"/api/b2b/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(team_project)
    
    @pytest.mark.asyncio
    async def test_update_project(self, api_client, domain_test_data, team_project):
        """Test updating project"""
        response = await api_client.put(
            f"/api/b2b/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={"name": "Updated Project Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project Name"
    
    @pytest.mark.asyncio
    async def test_archive_project(self, api_client, domain_test_data, team_project):
        """Test archiving a project"""
        response = await api_client.put(
            f"/api/b2b/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={"status": "archived"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"
    
    @pytest.mark.asyncio
    async def test_delete_project(self, api_client, domain_test_data, team_project):
        """Test deleting a project"""
        response = await api_client.delete(
            f"/api/b2b/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 204
        
        # Verify project is deleted (returns 403 because access check fails first)
        response = await api_client.get(
            f"/api/b2b/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_non_team_member_cannot_access_project(
        self,
        api_client,
        domain_test_data,
        team_project
    ):
        """Test user from different team cannot access project"""
        response = await api_client.get(
            f"/api/b2b/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['other_team_member_token']}"}
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(
        self,
        api_client,
        domain_test_data,
        team_project,
        tenant2_project
    ):
        """Test projects are isolated by tenant"""
        # Tenant 1 owner cannot see Tenant 2 project
        response = await api_client.get(
            f"/api/b2b/projects/{tenant2_project}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 403
        
        # Tenant 2 owner cannot see Tenant 1 project
        response = await api_client.get(
            f"/api/b2b/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['tenant2_owner_token']}"}
        )
        assert response.status_code == 403
