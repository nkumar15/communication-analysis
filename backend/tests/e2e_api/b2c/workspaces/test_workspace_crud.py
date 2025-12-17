"""
Test B2C Workspace CRUD Operations
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from core.config import settings


@pytest.mark.asyncio
class TestWorkspaceCRUD:
    """Test workspace creation, retrieval, update, and deletion"""
    
    async def test_list_workspaces_returns_personal_workspace(
        self, api_client: AsyncClient, workspace_owner
    ):
        """User should see their personal workspace in the list"""
        response = await api_client.get(
            f"{"http://test"}/api/b2c/workspaces/",
            headers={"Authorization": f"Bearer {workspace_owner['auth_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "workspaces" in data
        assert len(data["workspaces"]) >= 1
        
        # Should include personal workspace
        workspace_ids = [w["id"] for w in data["workspaces"]]
        assert str(workspace_owner["workspace"].id) in workspace_ids
    
    
    async def test_create_team_workspace_requires_premium(
        self, api_client: AsyncClient, workspace_owner
    ):
        """Free tier users cannot create team workspaces"""
        response = await api_client.post(
            f"{"http://test"}/api/b2c/workspaces/",
            headers={"Authorization": f"Bearer {workspace_owner['auth_token']}"},
            json={"name": "Team Workspace Attempt"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "premium" in data["detail"].lower() or "subscription" in data["detail"].lower()
    
    
    async def test_create_team_workspace_with_premium(
        self, api_client: AsyncClient, premium_workspace_owner
    ):
        """Premium users can create team workspaces"""
        response = await api_client.post(
            f"{"http://test"}/api/b2c/workspaces/",
            headers={"Authorization": f"Bearer {premium_workspace_owner['auth_token']}"},
            json={"name": "My Team Workspace"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Team Workspace"
        assert data["type"] == "team"
        assert data["subscription_tier"] == "premium"
        assert data["member_count"] == 1
        assert "id" in data
    
    
    async def test_get_workspace_details(
        self, api_client: AsyncClient, team_workspace, premium_workspace_owner
    ):
        """Get workspace details including members"""
        response = await api_client.get(
            f"{"http://test"}/api/b2c/workspaces/{team_workspace.id}",
            headers={"Authorization": f"Bearer {premium_workspace_owner['auth_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(team_workspace.id)
        assert data["name"] == "Test Team Workspace"
        assert data["type"] == "team"
        assert "members" in data
        assert len(data["members"]) >= 1
        
        # Owner should be in members
        owner_in_members = any(
            m["user_id"] == str(premium_workspace_owner["user"].id) 
            for m in data["members"]
        )
        assert owner_in_members
    
    
    async def test_get_workspace_details_requires_membership(
        self, api_client: AsyncClient, team_workspace, workspace_owner
    ):
        """Non-members cannot view workspace details"""
        response = await api_client.get(
            f"{"http://test"}/api/b2c/workspaces/{team_workspace.id}",
            headers={"Authorization": f"Bearer {workspace_owner['auth_token']}"}
        )
        
        assert response.status_code == 404
    
    
    async def test_update_workspace_settings(
        self, api_client: AsyncClient, team_workspace, premium_workspace_owner
    ):
        """Owner can update workspace name and settings"""
        new_name = f"Updated Workspace {uuid4().hex[:6]}"
        new_settings = {"theme": "dark", "notifications": True}
        
        response = await api_client.patch(
            f"{"http://test"}/api/b2c/workspaces/{team_workspace.id}",
            headers={"Authorization": f"Bearer {premium_workspace_owner['auth_token']}"},
            json={"name": new_name, "settings": new_settings}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name
        assert data["settings"] == new_settings
    
    
    async def test_update_workspace_requires_admin_role(
        self, api_client: AsyncClient, workspace_with_members
    ):
        """Members cannot update workspace settings"""
        response = await api_client.patch(
            f"{"http://test"}/api/b2c/workspaces/{workspace_with_members['workspace'].id}",
            headers={"Authorization": f"Bearer {workspace_with_members['member']['auth_token']}"},
            json={"name": "Unauthorized Update"}
        )
        
        assert response.status_code == 403
    
    
    async def test_delete_team_workspace(
        self, api_client: AsyncClient, team_workspace, premium_workspace_owner, db_session
    ):
        """Owner can delete team workspace"""
        workspace_id = str(team_workspace.id)
        
        response = await api_client.delete(
            f"{"http://test"}/api/b2c/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {premium_workspace_owner['auth_token']}"}
        )
        
        assert response.status_code == 204
        
        # Verify workspace is deleted
        from sqlalchemy import select
        from services.b2c.models.workspace import Workspace
        result = await db_session.execute(
            select(Workspace).where(Workspace.id == team_workspace.id)
        )
        deleted_workspace = result.scalar_one_or_none()
        assert deleted_workspace is None
    
    
    async def test_delete_personal_workspace_forbidden(
        self, api_client: AsyncClient, workspace_owner
    ):
        """Cannot delete personal workspace"""
        response = await api_client.delete(
            f"{"http://test"}/api/b2c/workspaces/{workspace_owner['workspace'].id}",
            headers={"Authorization": f"Bearer {workspace_owner['auth_token']}"}
        )
        
        assert response.status_code == 400
        assert "personal" in response.json()["detail"].lower()
    
    
    async def test_delete_workspace_requires_owner_role(
        self, api_client: AsyncClient, workspace_with_members
    ):
        """Only owner can delete workspace"""
        response = await api_client.delete(
            f"{"http://test"}/api/b2c/workspaces/{workspace_with_members['workspace'].id}",
            headers={"Authorization": f"Bearer {workspace_with_members['member']['auth_token']}"}
        )
        
        assert response.status_code == 403
    
    
    async def test_workspace_quota_enforcement_premium(
        self, api_client: AsyncClient, premium_workspace_owner
    ):
        """Premium users limited to 3 team workspaces"""
        # Create 3 team workspaces
        for i in range(3):
            response = await api_client.post(
                f"{"http://test"}/api/b2c/workspaces/",
                headers={"Authorization": f"Bearer {premium_workspace_owner['auth_token']}"},
                json={"name": f"Team Workspace {i+1}"}
            )
            assert response.status_code == 201
        
        # 4th should fail
        response = await api_client.post(
            f"{"http://test"}/api/b2c/workspaces/",
            headers={"Authorization": f"Bearer {premium_workspace_owner['auth_token']}"},
            json={"name": "4th Workspace - Should Fail"}
        )
        
        assert response.status_code == 403
        assert "limit" in response.json()["detail"].lower()
