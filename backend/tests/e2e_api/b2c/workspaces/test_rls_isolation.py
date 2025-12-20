"""
Test B2C Workspace RLS (Row Level Security) Isolation
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from sqlalchemy import select, text

from core.config import settings
from services.b2c.models.workspace import Workspace
from services.b2c.models.workspace_member import WorkspaceMember


@pytest.mark.asyncio
class TestWorkspaceRLSIsolation:
    """Test that users can only access their own workspace data via RLS"""
    
    async def test_user_cannot_see_other_workspaces(
        self, api_client: AsyncClient, team_workspace, workspace_owner, premium_workspace_owner
    ):
        """User A cannot access User B's workspace"""
        # workspace_owner tries to access premium_workspace_owner's team workspace
        response = await api_client.get(
            f"{"http://test"}/api/b2c/workspaces/{team_workspace.id}",
            headers={"Authorization": f"Bearer {workspace_owner['auth_token']}"}
        )
        
        assert response.status_code == 403  # Explicit permission check blocks access
    
    
    async def test_removed_member_loses_access_immediately(
        self, api_client: AsyncClient, workspace_with_members, db_session
    ):
        """Removed member immediately loses workspace access via RLS"""
        workspace_id = str(workspace_with_members['workspace'].id)
        member_id = str(workspace_with_members['member']['user'].id)
        
        # Member can initially access workspace
        response = await api_client.get(
            f"{"http://test"}/api/b2c/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {workspace_with_members['member']['auth_token']}"}
        )
        assert response.status_code == 200
        
        # Owner removes member
        await api_client.delete(
            f"{"http://test"}/api/b2c/workspaces/{workspace_id}/members/{member_id}",
            headers={"Authorization": f"Bearer {workspace_with_members['owner']['auth_token']}"}
        )
        
        # Member can no longer access workspace
        response = await api_client.get(
            f"{"http://test"}/api/b2c/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {workspace_with_members['member']['auth_token']}"}
        )
        assert response.status_code == 403  # Explicit access check after removal
    
    
    async def test_user_only_sees_their_workspaces_in_list(
        self, api_client: AsyncClient, workspace_with_members
    ):
        """List endpoint only returns workspaces user has access to"""
        # Owner sees their workspaces
        response = await api_client.get(
            f"{"http://test"}/api/b2c/workspaces",
            headers={"Authorization": f"Bearer {workspace_with_members['owner']['auth_token']}"}
        )
        assert response.status_code == 200
        owner_workspaces = response.json()["workspaces"]
        
        # Member sees their workspaces (should include workspace_with_members)
        response = await api_client.get(
            f"{"http://test"}/api/b2c/workspaces",
            headers={"Authorization": f"Bearer {workspace_with_members['member']['auth_token']}"}
        )
        assert response.status_code == 200
        member_workspaces = response.json()["workspaces"]
        
        # Member should see the shared workspace
        member_workspace_ids = [w["id"] for w in member_workspaces]
        assert str(workspace_with_members['workspace'].id) in member_workspace_ids
        
        # But shouldn't see all of owner's personal workspaces
        assert len(member_workspaces) <= len(owner_workspaces)
    
    
    async def test_rls_context_properly_set(
        self, api_client: AsyncClient, workspace_owner, db_session
    ):
        """Verify RLS context is set on all API calls"""
        from core.rls import rls_service
        
        # Set context for workspace_owner
        await rls_service.set_user_context(db_session, workspace_owner['user'].id)
        
        # Query should only return workspace_owner's workspaces
        result = await db_session.execute(
            select(Workspace)
        )
        workspaces = result.scalars().all()
        
        # All workspaces should belong to workspace_owner or have them as member
        for workspace in workspaces:
            if workspace.type.value == 'personal':
                assert workspace.owner_id == workspace_owner['user'].id
            else:
                # Check membership
                member_result = await db_session.execute(
                    select(WorkspaceMember).where(
                        WorkspaceMember.workspace_id == workspace.id,
                        WorkspaceMember.user_id == workspace_owner['user'].id
                    )
                )
                assert member_result.scalar_one_or_none() is not None
    
    
    async def test_workspace_members_isolation(
        self, api_client: AsyncClient, workspace_with_members, workspace_owner, db_session
    ):
        """Users can only see members of workspaces they belong to"""
        from core.rls import rls_service
        
        # workspace_owner (not a member) cannot query workspace members
        await rls_service.set_user_context(db_session, workspace_owner['user'].id)
        
        result = await db_session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_with_members['workspace'].id
            )
        )
        members = result.scalars().all()
        
        # Should return empty due to RLS (workspace_owner not a member)
        assert len(members) == 0
        
        # But workspace owner should see their own workspace members
        await rls_service.set_user_context(db_session, workspace_with_members['owner']['user'].id)
        
        result = await db_session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_with_members['workspace'].id
            )
        )
        members = result.scalars().all()
        
        # Should return members
        assert len(members) == 2  # owner + member
    
    
    async def test_invitation_visibility_rls(
        self, api_client: AsyncClient, workspace_invitation, workspace_owner, db_session
    ):
        """Users can only see invitations to their email or in their workspaces"""
        from services.b2c.models.workspace_invitation import WorkspaceInvitation
        from core.rls import rls_service
        
        # workspace_owner (not in workspace) cannot see invitation
        await rls_service.set_user_context(db_session, workspace_owner['user'].id)
        
        result = await db_session.execute(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.id == workspace_invitation['invitation'].id
            )
        )
        invisible_invitation = result.scalar_one_or_none()
        assert invisible_invitation is None  # RLS blocks
        
        # Inviter can see invitation
        await rls_service.set_user_context(db_session, workspace_invitation['inviter']['user'].id)
        
        result = await db_session.execute(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.id == workspace_invitation['invitation'].id
            )
        )
        visible_invitation = result.scalar_one_or_none()
        assert visible_invitation is not None
    
    
    async def test_deleted_workspace_cascades_members(
        self, api_client: AsyncClient, team_workspace, premium_workspace_owner, db_session
    ):
        """Deleting workspace cascades to members via database constraints"""
        workspace_id = team_workspace.id
        
        # Delete workspace
        response = await api_client.delete(
            f"{"http://test"}/api/b2c/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {premium_workspace_owner['auth_token']}"}
        )
        assert response.status_code == 204
        
        # Verify members are also deleted (CASCADE)
        from core.rls import rls_service
        await rls_service.set_user_context(db_session, premium_workspace_owner['user'].id)
        
        result = await db_session.execute(
            select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
        )
        members = result.scalars().all()
        assert len(members) == 0
