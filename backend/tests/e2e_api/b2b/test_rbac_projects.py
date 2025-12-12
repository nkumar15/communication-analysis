
import pytest
from httpx import AsyncClient
from uuid import uuid4
from tests.conftest import (
    create_test_user,
    create_mock_firebase_token,
    encode_mock_jwt
)

@pytest.mark.integration
class TestProjectRBAC:
    
    @pytest.mark.asyncio
    async def test_team_manager_can_create_project(self, api_client: AsyncClient, b2b_test_setup):
        """
        Test that a user with 'member' tenant role but 'team_manager' scope
        can create a project in their team. (Currently failing)
        """
        setup = b2b_test_setup
        tenant = setup["tenant"]
        token = setup["token"]
        
        # 1. Create a Team (as Admin)
        t_resp = await api_client.post(
            "/api/b2b/teams/", 
            json={"name": f"Project Team {uuid4().hex[:4]}"}, 
            headers={"Authorization": f"Bearer {token}"}
        )
        assert t_resp.status_code == 201
        team_id = t_resp.json()["id"]
        
        # 2. Create User (Standard Member)
        # 'member' role usually does NOT have projects:write globally
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
        
        # 4. Generate Token for User
        user_token = encode_mock_jwt(create_mock_firebase_token(
            uid=user.firebase_uid,
            email=user.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # 5. Attempt Create Project
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
            setup['session'],
            tenant_id=tenant.id,
            email=f"contrib_{uuid4().hex[:4]}@{tenant.domain}",
            role_slug="member"
        )
        
        # 3. Add as Team Contributor
        await api_client.post(
            f"/api/b2b/teams/{team_id}/members",
            json={"user_id": str(user.id), "team_role": "team_contributor"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 4. Login as Contributor
        user_token = encode_mock_jwt(create_mock_firebase_token(
            uid=user.firebase_uid,
            email=user.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # 5. Attempt Create Project (Should Fail)
        p_resp = await api_client.post(
            "/api/domain/projects",
            json={
                "name": "Contributor Project",
                "description": "Should fail",
                "team_id": team_id
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert p_resp.status_code == 403, "Contributor should not be able to create projects"
        
        # 6. Create a project as Admin for task test
        admin_p_resp = await api_client.post(
            "/api/domain/projects",
            json={
                "name": "Admin Project for Tasks",
                "description": "For task testing",
                "team_id": team_id
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        project_id = admin_p_resp.json()["id"]
        
        # 7. Attempt Create Task (Should Succeed)
        t_resp = await api_client.post(
            "/api/domain/tasks",
            json={
                "project_id": project_id,
                "title": "Contributor Task",
                "description": "I can create this"
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert t_resp.status_code == 201, "Contributor should be able to create tasks"
