
"""
Integration tests for Projects API

Tests cover:
- CRUD operations
- Team-scoped access control
- Multi-tenant isolation
- Granular RBAC (Team Manager vs Contributor)
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from tests.conftest import (
    create_test_user,
    create_mock_firebase_token,
    encode_mock_jwt
)


class TestProjectsAPI:
    """Test suite for basic Projects endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_project(self, api_client, domain_test_data):
        """Test creating a project"""
        response = await api_client.post(
            "/api/domain/projects",
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
            "/api/domain/projects",
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
            "/api/domain/projects",
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
            "/api/domain/projects",
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
            f"/api/domain/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(team_project)
    
    @pytest.mark.asyncio
    async def test_update_project(self, api_client, domain_test_data, team_project):
        """Test updating project"""
        response = await api_client.put(
            f"/api/domain/projects/{team_project}",
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
            f"/api/domain/projects/{team_project}",
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
            f"/api/domain/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 204
        
        # Verify project is deleted (returns 403 because access check fails first)
        response = await api_client.get(
            f"/api/domain/projects/{team_project}",
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
            f"/api/domain/projects/{team_project}",
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
            f"/api/domain/projects/{tenant2_project}",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 403
        
        # Tenant 2 owner cannot see Tenant 1 project
        response = await api_client.get(
            f"/api/domain/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['tenant2_owner_token']}"}
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestProjectRBAC:
    """Test granular permissions (Team Roles)"""
    
    @pytest.mark.asyncio
    async def test_team_manager_can_create_project(self, api_client: AsyncClient, b2b_test_setup):
        """
        Test that a user with 'member' tenant role but 'team_manager' scope
        can create a project in their team. (Granular check)
        """
        setup = b2b_test_setup
        tenant = setup["tenant"]
        token = setup["token"]
        
        # 1. Create a Team
        t_resp = await api_client.post(
            "/api/b2b/teams/", 
            json={"name": f"Project Team {uuid4().hex[:4]}"}, 
            headers={"Authorization": f"Bearer {token}"}
        )
        assert t_resp.status_code == 201
        team_id = t_resp.json()["id"]
        
        # 2. Create User (Standard Member)
        user = await create_test_user(
            setup['session'],
            tenant_id=tenant.id,
            email=f"manager_{uuid4().hex[:4]}@{tenant.domain}",
            role_slug="member" 
        )
        
        # 3. Add as Team Manager
        await api_client.post(
            f"/api/b2b/teams/{team_id}/members",
            json={"user_id": str(user.id), "team_role": "team_manager"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        user_token = encode_mock_jwt(create_mock_firebase_token(
            uid=user.firebase_uid, email=user.email, firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        p_resp = await api_client.post(
            "/api/domain/projects",
            json={
                "name": "Manager Project",
                "description": "Created by team manager",
                "team_id": team_id
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert p_resp.status_code == 201
        data = p_resp.json()
        assert data["name"] == "Manager Project"

    @pytest.mark.asyncio
    async def test_team_contributor_permissions(self, api_client: AsyncClient, b2b_test_setup):
        """
        Test granular contributor permissions:
        - Cannot create projects (read only)
        - Can create tasks (write)
        """
        setup = b2b_test_setup
        tenant = setup["tenant"]
        token = setup["token"]
        
        # 1. Create a Team
        t_resp = await api_client.post(
            "/api/b2b/teams/", 
            json={"name": f"Contrib Team {uuid4().hex[:4]}"}, 
            headers={"Authorization": f"Bearer {token}"}
        )
        team_id = t_resp.json()["id"]
        
        # 2. Create User (Contributor)
        user = await create_test_user(
            setup['session'], tenant_id=tenant.id, email=f"contrib_{uuid4().hex[:4]}@{tenant.domain}", role_slug="member"
        )
        
        # 3. Add as Team Contributor
        await api_client.post(
            f"/api/b2b/teams/{team_id}/members",
            json={"user_id": str(user.id), "team_role": "team_contributor"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        user_token = encode_mock_jwt(create_mock_firebase_token(
            uid=user.firebase_uid, email=user.email, firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # 5. Attempt Create Project (Should Fail)
        p_resp = await api_client.post(
            "/api/domain/projects",
            json={"name": "Contributor Project", "description": "Should fail", "team_id": team_id},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert p_resp.status_code == 403, "Contributor should not be able to create projects"
        
        # 6. Create a project as Admin for task test
        admin_p_resp = await api_client.post(
            "/api/domain/projects",
            json={"name": "Admin Project for Tasks", "description": "For task testing", "team_id": team_id},
            headers={"Authorization": f"Bearer {token}"}
        )
        project_id = admin_p_resp.json()["id"]
        
        # 7. Attempt Create Task (Should Succeed)
        t_resp = await api_client.post(
            "/api/domain/tasks",
            json={"project_id": project_id, "title": "Contributor Task", "description": "I can create this"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert t_resp.status_code == 201, "Contributor should be able to create tasks"


class TestProjectsViewerRestrictions:
    """Test that Viewer role cannot perform write operations"""
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_create_project(self, api_client, domain_test_data):
        """Viewer should get 403 when trying to create a project"""
        response = await api_client.post(
            "/api/domain/projects",
            headers={"Authorization": f"Bearer {domain_test_data['viewer_token']}"},
            json={
                "team_id": str(domain_test_data['default_team'].id),
                "name": "Viewer Project",
                "description": "Should fail"
            }
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_update_project(
        self, api_client, domain_test_data, team_project
    ):
        """Viewer should get 403 when trying to update a project"""
        response = await api_client.put(
            f"/api/domain/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['viewer_token']}"},
            json={"name": "Hacked Name"}
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_delete_project(
        self, api_client, domain_test_data, team_project
    ):
        """Viewer should get 403 when trying to delete a project"""
        response = await api_client.delete(
            f"/api/domain/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['viewer_token']}"}
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_viewer_can_read_project(
        self, api_client, domain_test_data, team_project
    ):
        """Viewer should be able to read projects in their team"""
        response = await api_client.get(
            f"/api/domain/projects/{team_project}",
            headers={"Authorization": f"Bearer {domain_test_data['viewer_token']}"}
        )
        assert response.status_code == 200


class TestProjectsValidation:
    """Test input validation for Projects API"""
    
    @pytest.mark.asyncio
    async def test_create_project_empty_name(self, api_client, domain_test_data):
        """Test that empty project name is rejected"""
        response = await api_client.post(
            "/api/domain/projects",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "team_id": str(domain_test_data['default_team'].id),
                "name": "",
                "description": "Should fail"
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_project_missing_team_id(self, api_client, domain_test_data):
        """Test that missing team_id is rejected"""
        response = await api_client.post(
            "/api/domain/projects",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "name": "Project Without Team"
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_project_invalid_team_id(self, api_client, domain_test_data):
        """Test that invalid team_id format is rejected"""
        response = await api_client.post(
            "/api/domain/projects",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"},
            json={
                "team_id": "not-a-uuid",
                "name": "Project"
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_project_invalid_id(self, api_client, domain_test_data):
        """Test that invalid project ID returns 422"""
        response = await api_client.get(
            "/api/domain/projects/not-a-uuid",
            headers={"Authorization": f"Bearer {domain_test_data['owner_token']}"}
        )
        assert response.status_code == 422
