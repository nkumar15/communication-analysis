"""
Test B2C Workspace Invitation Flow
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from core.config import settings


@pytest.mark.asyncio
class TestWorkspaceInvitations:
    """Test invitation creation, acceptance, and cancellation"""
    
    async def test_invite_user_to_workspace(
        self, api_client: AsyncClient, team_workspace, premium_workspace_owner
    ):
        """Owner can invite users by email"""
        invitee_email = f"newuser-{uuid4().hex[:8]}@example.com"
        
        response = await api_client.post(
            f"{"http://test"}/api/b2c/workspaces/{team_workspace.id}/invite",
            headers={"Authorization": f"Bearer {premium_workspace_owner['auth_token']}"},
            json={"email": invitee_email, "role": "member"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == invitee_email
        assert data["role"] == "member"
        assert "invitation_token" in data
        assert "expires_at" in data
    
    
    async def test_member_cannot_invite(
        self, api_client: AsyncClient, workspace_with_members
    ):
        """Regular members cannot invite users"""
        response = await api_client.post(
            f"{"http://test"}/api/b2c/workspaces/{workspace_with_members['workspace'].id}/invite",
            headers={"Authorization": f"Bearer {workspace_with_members['member']['auth_token']}"},
            json={"email": "someone@example.com", "role": "member"}
        )
        
        assert response.status_code == 403
    
    
    async def test_prevent_duplicate_invitation(
        self, api_client: AsyncClient, workspace_invitation
    ):
        """Cannot invite same email twice"""
        response = await api_client.post(
            f"{"http://test"}/api/b2c/workspaces/{workspace_invitation['workspace'].id}/invite",
            headers={"Authorization": f"Bearer {workspace_invitation['inviter']['auth_token']}"},
            json={"email": workspace_invitation['invitee_email'], "role": "member"}
        )
        
        assert response.status_code == 422  # FastAPI validation error
        assert "already" in response.json()["detail"].lower()
    
    
    async def test_prevent_inviting_existing_member(
        self, api_client: AsyncClient, workspace_with_members
    ):
        """Cannot invite user who is already a member"""
        response = await api_client.post(
            f"{"http://test"}/api/b2c/workspaces/{workspace_with_members['workspace'].id}/invite",
            headers={"Authorization": f"Bearer {workspace_with_members['owner']['auth_token']}"},
            json={"email": workspace_with_members['member']['email'], "role": "member"}
        )
        
        assert response.status_code == 422  # FastAPI validation error
        assert "already a member" in response.json()["detail"].lower()
    
    
    async def test_get_invitation_details_by_token(
        self, api_client: AsyncClient, workspace_invitation
    ):
        """Anyone can view invitation details with token (public endpoint)"""
        response = await api_client.get(
            f"{"http://test"}/api/b2c/invitations/{workspace_invitation['invitation'].invitation_token}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == workspace_invitation['invitee_email']
        assert data["role"] == "member"
        assert "workspace" in data
        assert data["workspace"]["name"] == workspace_invitation['workspace'].name
        assert "inviter" in data
    
    
    async def test_accept_invitation(
        self, api_client: AsyncClient, workspace_invitation, team_member_user, db_session
    ):
        """User can accept invitation with matching email"""
        # Create user with matching email
        from tests.conftest import create_b2c_user, create_b2c_mock_token, encode_mock_jwt
        from core.rls import rls_service
        
        firebase_uid = f"firebase-{uuid4().hex[:12]}"
        user = await create_b2c_user(
            db_session, 
            workspace_invitation['invitee_email'],  # Same email as invitation
            firebase_uid, 
            "Invited User"
        )
        await db_session.flush()
        
        # Set RLS for new user
        await rls_service.set_user_context(db_session, user.id)
        
        mock_token_data = create_b2c_mock_token(firebase_uid, workspace_invitation['invitee_email'])
        auth_token = encode_mock_jwt(mock_token_data)
        
        response = await api_client.post(
            f"{"http://test"}/api/b2c/invitations/{workspace_invitation['invitation'].invitation_token}/accept",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == str(workspace_invitation['workspace'].id)
        assert data["role"] == "member"
        
        # Verify user is now a member
        from sqlalchemy import select
        from services.b2c.models.workspace_member import WorkspaceMember
        result = await db_session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_invitation['workspace'].id,
                WorkspaceMember.user_id == user.id
            )
        )
        member = result.scalar_one_or_none()
        assert member is not None
        assert member.role == "member"
    
    
    async def test_cannot_accept_with_wrong_email(
        self, api_client: AsyncClient, workspace_invitation, team_member_user
    ):
        """User with different email cannot accept invitation"""
        response = await api_client.post(
            f"{"http://test"}/api/b2c/invitations/{workspace_invitation['invitation'].invitation_token}/accept",
            headers={"Authorization": f"Bearer {team_member_user['auth_token']}"}
        )
        
        assert response.status_code == 403
        assert "email" in response.json()["detail"].lower()
    
    
    async def test_expired_invitation_rejected(
        self, api_client: AsyncClient, db_session, team_workspace, premium_workspace_owner
    ):
        """Expired invitations cannot be viewed or accepted"""
        from services.b2c.models.workspace_invitation import WorkspaceInvitation
        from core.rls import rls_service
        
        await rls_service.set_user_context(db_session, premium_workspace_owner['user'].id)
        
        # Create expired invitation
        expired_invitation = WorkspaceInvitation(
            workspace_id=team_workspace.id,
            email=f"expired-{uuid4().hex[:8]}@example.com",
            role='member',
            invitation_token=f"token_{uuid4().hex}",
            invited_by=premium_workspace_owner['user'].id,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)  # Expired
        )
        db_session.add(expired_invitation)
        await db_session.flush()
        
        response = await api_client.get(
            f"{"http://test"}/api/b2c/invitations/{expired_invitation.invitation_token}"
        )
        
        assert response.status_code == 410  # Gone
        assert "expired" in response.json()["detail"].lower()
    
    
    async def test_cancel_invitation(
        self, api_client: AsyncClient, workspace_invitation, db_session
    ):
        """Inviter can cancel invitation (soft delete)"""
        invitation_id = str(workspace_invitation['invitation'].id)
        
        response = await api_client.delete(
            f"{"http://test"}/api/b2c/invitations/{invitation_id}",
            headers={"Authorization": f"Bearer {workspace_invitation['inviter']['auth_token']}"}
        )
        
        assert response.status_code == 204
        
        # Verify invitation is soft deleted
        from sqlalchemy import select
        from services.b2c.models.workspace_invitation import WorkspaceInvitation
        result = await db_session.execute(
            select(WorkspaceInvitation).where(WorkspaceInvitation.id == workspace_invitation['invitation'].id)
        )
        cancelled_invitation = result.scalar_one_or_none()
        assert cancelled_invitation is not None
        assert cancelled_invitation.cancelled_at is not None
        assert cancelled_invitation.cancelled_by == workspace_invitation['inviter']['user'].id
    
    
    async def test_non_inviter_cannot_cancel(
        self, api_client: AsyncClient, workspace_invitation, team_member_user
    ):
        """Only inviter or admin can cancel invitation"""
        response = await api_client.delete(
            f"{"http://test"}/api/b2c/invitations/{workspace_invitation['invitation'].id}",
            headers={"Authorization": f"Bearer {team_member_user['auth_token']}"}
        )
        
        assert response.status_code == 403
    
    
    async def test_cannot_accept_cancelled_invitation(
        self, api_client: AsyncClient, workspace_invitation, db_session
    ):
        """Cancelled invitations cannot be accepted"""
        from datetime import datetime
        from core.rls import rls_service
        
        # Cancel invitation
        await rls_service.set_user_context(db_session, workspace_invitation['inviter']['user'].id)
        workspace_invitation['invitation'].cancelled_at = datetime.now(timezone.utc)
        workspace_invitation['invitation'].cancelled_by = workspace_invitation['inviter']['user'].id
        await db_session.flush()
        
        # Try to view it
        response = await api_client.get(
            f"{"http://test"}/api/b2c/invitations/{workspace_invitation['invitation'].invitation_token}"
        )
        
        assert response.status_code == 404  # Cancelled invitations filtered out
    
    
    async def test_invalid_role_in_invitation(
        self, api_client: AsyncClient, team_workspace, premium_workspace_owner
    ):
        """Invalid roles are rejected in invitations"""
        response = await api_client.post(
            f"{"http://test"}/api/b2c/workspaces/{team_workspace.id}/invite",
            headers={"Authorization": f"Bearer {premium_workspace_owner['auth_token']}"},
            json={"email": "test@example.com", "role": "superadmin"}
        )
        
        assert response.status_code == 400
