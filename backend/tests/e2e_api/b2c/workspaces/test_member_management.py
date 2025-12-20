"""
Test B2C Workspace Member Management
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from core.config import settings


@pytest.mark.asyncio
class TestWorkspaceMemberManagement:
    """Test workspace member listing, role updates, and removal"""
    
    @pytest.mark.xfail(reason="RLS transaction isolation issue in tests hides member rows")
    async def test_list_workspace_members(
        self, api_client: AsyncClient, workspace_with_members
    ):
        response = await api_client.get(
            f"{"http://test"}/api/b2c/workspaces/{workspace_with_members['workspace'].id}/members",
            headers={"Authorization": f"Bearer {workspace_with_members['owner']['auth_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "members" in data
        assert len(data["members"]) == 2  # owner + member
        assert len(data["members"]) == 2  # owner + member
        
        # Check owner is present
        owner_present = any(
            m["role"] == "owner" and m["user_id"] == str(workspace_with_members['owner']['user'].id)
            for m in data["members"]
        )
        assert owner_present
        
        # Check member is present
        member_present = any(
            m["role"] == "member" and m["user_id"] == str(workspace_with_members['member']['user'].id)
            for m in data["members"]
        )
        assert member_present
    
    
    async def test_update_member_role_as_owner(
        self, api_client: AsyncClient, workspace_with_members
    ):
        """Owner can update member roles"""
        response = await api_client.patch(
            f"{"http://test"}/api/b2c/workspaces/{workspace_with_members['workspace'].id}/members/{workspace_with_members['member']['user'].id}",
            headers={"Authorization": f"Bearer {workspace_with_members['owner']['auth_token']}"},
            json={"role": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert data["user_id"] == str(workspace_with_members['member']['user'].id)
    
    
    async def test_cannot_update_owner_role(
        self, api_client: AsyncClient, workspace_with_members
    ):
        """Cannot demote owner role"""
        response = await api_client.patch(
            f"{"http://test"}/api/b2c/workspaces/{workspace_with_members['workspace'].id}/members/{workspace_with_members['owner']['user'].id}",
            headers={"Authorization": f"Bearer {workspace_with_members['owner']['auth_token']}"},
            json={"role": "member"}
        )
        
        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()
    
    
    async def test_member_cannot_update_roles(
        self, api_client: AsyncClient, workspace_with_members, team_member_user
    ):
        """Regular members cannot update roles"""
        # Create another member to try to update
        response = await api_client.patch(
            f"{"http://test"}/api/b2c/workspaces/{workspace_with_members['workspace'].id}/members/{workspace_with_members['owner']['user'].id}",
            headers={"Authorization": f"Bearer {workspace_with_members['member']['auth_token']}"},
            json={"role": "admin"}
        )
        
        assert response.status_code == 403
    
    
    async def test_invalid_role_rejected(
        self, api_client: AsyncClient, workspace_with_members
    ):
        """Invalid roles are rejected"""
        response = await api_client.patch(
            f"{"http://test"}/api/b2c/workspaces/{workspace_with_members['workspace'].id}/members/{workspace_with_members['member']['user'].id}",
            headers={"Authorization": f"Bearer {workspace_with_members['owner']['auth_token']}"},
            json={"role": "superadmin"}
        )
        
        assert response.status_code == 400
    
    
    async def test_remove_member_as_owner(
        self, api_client: AsyncClient, workspace_with_members, db_session
    ):
        """Owner can remove members"""
        member_id = str(workspace_with_members['member']['user'].id)
        workspace_id = str(workspace_with_members['workspace'].id)
        
        response = await api_client.delete(
            f"{"http://test"}/api/b2c/workspaces/{workspace_id}/members/{member_id}",
            headers={"Authorization": f"Bearer {workspace_with_members['owner']['auth_token']}"}
        )
        
        assert response.status_code == 204
        
        # Verify member removed
        from sqlalchemy import select
        from services.b2c.models.workspace_member import WorkspaceMember
        result = await db_session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_with_members['workspace'].id,
                WorkspaceMember.user_id == workspace_with_members['member']['user'].id
            )
        )
        removed_member = result.scalar_one_or_none()
        assert removed_member is None
    
    
    async def test_cannot_remove_owner(
        self, api_client: AsyncClient, workspace_with_members
    ):
        """Cannot remove workspace owner"""
        response = await api_client.delete(
            f"{"http://test"}/api/b2c/workspaces/{workspace_with_members['workspace'].id}/members/{workspace_with_members['owner']['user'].id}",
            headers={"Authorization": f"Bearer {workspace_with_members['owner']['auth_token']}"}
        )
        
        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()
    
    
    async def test_member_cannot_remove_others(
        self, api_client: AsyncClient, workspace_with_members
    ):
        """Regular members cannot remove other members"""
        response = await api_client.delete(
            f"{"http://test"}/api/b2c/workspaces/{workspace_with_members['workspace'].id}/members/{workspace_with_members['owner']['user'].id}",
            headers={"Authorization": f"Bearer {workspace_with_members['member']['auth_token']}"}
        )
        
        assert response.status_code == 403
    
    
    async def test_removed_member_loses_access(
        self, api_client: AsyncClient, workspace_with_members, db_session
    ):
        """Removed member immediately loses workspace access"""
        member_id = str(workspace_with_members['member']['user'].id)
        workspace_id = str(workspace_with_members['workspace'].id)
        
        # Remove member
        response = await api_client.delete(
            f"{"http://test"}/api/b2c/workspaces/{workspace_id}/members/{member_id}",
            headers={"Authorization": f"Bearer {workspace_with_members['owner']['auth_token']}"}
        )
        assert response.status_code == 204
        
        # Try to access workspace details as removed member
        response = await api_client.get(
            f"{"http://test"}/api/b2c/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {workspace_with_members['member']['auth_token']}"}
        )
        
        assert response.status_code == 404  # RLS blocks access
