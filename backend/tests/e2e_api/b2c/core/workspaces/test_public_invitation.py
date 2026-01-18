"""
Test B2C Public Invitation Endpoint

Tests for the public invitation retrieval endpoint that allows
unauthenticated users to view invitation details before accepting.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from core.config import settings


@pytest.mark.asyncio
class TestPublicInvitationEndpoint:
    """Test public invitation endpoint (no authentication required)"""
    
    async def test_get_invitation_without_auth(
        self, api_client: AsyncClient, workspace_invitation
    ):
        """Unauthenticated users can view invitation details"""
        invitation = workspace_invitation['invitation']
        
        # No authentication header
        response = await api_client.get(
            f"http://test/api/b2c/invitations/{invitation.invitation_token}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['email'] == invitation.email
        assert data['role'] == invitation.role
        assert data['workspace']['id'] == str(invitation.workspace_id)
        assert data['workspace']['name'] == invitation.workspace.name
        assert 'inviter' in data
        assert data['inviter']['email'] == workspace_invitation['inviter']['user'].email
    
    async def test_get_invitation_returns_workspace_info(
        self, api_client: AsyncClient, workspace_invitation
    ):
        """Invitation includes workspace and inviter details"""
        invitation = workspace_invitation['invitation']
        
        response = await api_client.get(
            f"http://test/api/b2c/invitations/{invitation.invitation_token}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify workspace details
        assert 'workspace' in data
        assert data['workspace']['name'] == invitation.workspace.name
        assert data['workspace']['type'] in ['personal', 'team']
        
        # Verify inviter details  
        assert 'inviter' in data
        assert 'email' in data['inviter']
    
    async def test_get_invitation_with_invalid_token(
        self, api_client: AsyncClient
    ):
        """Invalid tokens return 404"""
        fake_token = "invalid-token-123"
        
        response = await api_client.get(
            f"http://test/api/b2c/invitations/{fake_token}"
        )
        
        assert response.status_code == 404
        assert 'not found' in response.json()['detail'].lower()
    
    async def test_get_invitation_expired(
        self, api_client: AsyncClient, workspace_invitation, db_session
    ):
        """Expired invitations return 410 Gone"""
        invitation = workspace_invitation['invitation']
        
        # Manually expire the invitation
        invitation.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        await db_session.commit()
        
        response = await api_client.get(
            f"http://test/api/b2c/invitations/{invitation.invitation_token}"
        )
        
        assert response.status_code == 410
        assert 'expired' in response.json()['detail'].lower()
    
    async def test_get_invitation_already_accepted(
        self, api_client: AsyncClient, workspace_invitation, db_session
    ):
        """Already accepted invitations return 410 Gone"""
        invitation = workspace_invitation['invitation']
        
        # Mark as accepted
        invitation.accepted_at = datetime.now(timezone.utc)
        await db_session.commit()
        
        response = await api_client.get(
            f"http://test/api/b2c/invitations/{invitation.invitation_token}"
        )
        
        assert response.status_code == 410
        assert 'already been accepted' in response.json()['detail'].lower()
    
    async def test_get_invitation_cancelled(
        self, api_client: AsyncClient, workspace_invitation, db_session
    ):
        """Cancelled invitations return 404"""
        invitation = workspace_invitation['invitation']
        
        # Mark as cancelled
        invitation.cancelled_at = datetime.now(timezone.utc)
        await db_session.commit()
        
        response = await api_client.get(
            f"http://test/api/b2c/invitations/{invitation.invitation_token}"
        )
        
        assert response.status_code == 404
        assert 'not found' in response.json()['detail'].lower()
    
    async def test_get_invitation_rls_bypass(
        self, api_client: AsyncClient, workspace_invitation, workspace_owner
    ):
        """Public endpoint bypasses RLS - works without user context"""
        invitation = workspace_invitation['invitation']
        
        # Even if we authenticate as a different user, it should still work
        # (but we're testing without auth header to verify RLS bypass)
        response = await api_client.get(
            f"http://test/api/b2c/invitations/{invitation.invitation_token}"
        )
        
        assert response.status_code == 200
        # Should return invitation even though no RLS context is set
        data = response.json()
        assert data['id'] == str(invitation.id)
