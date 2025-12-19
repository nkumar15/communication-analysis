"""
E2E API Tests for Platform Invitations

Tests the complete invitation workflow:
- Creating invitations
- Listing invitations  
- Revoking invitations
- Validating tokens
- Permission enforcement
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from tests.conftest import (
    create_mock_firebase_token,
    encode_mock_jwt,
    create_platform_tenant,
    create_platform_user
)
from services.platform.models import PlatformInvitation, PlatformRole


@pytest.mark.integration
class TestPlatformInvitations:
    """Test platform invitations API endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_invitation_requires_authentication(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that creating invitations requires authentication"""
        response = await api_client.post(
            "/api/platform/invitations/",
            json={
                "email": "newadmin@platform.net",
                "role_id": "some-role-id"
            }
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_invitation_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test creating a platform invitation"""
        unique_email = f"admin-{uuid4().hex[:8]}@platform.net"
        invite_email = f"invited-{uuid4().hex[:8]}@platform.net"
        
        # Setup platform admin
        platform_tenant = await create_platform_tenant(db_session)
        admin = await create_platform_user(
            db_session,
            platform_tenant_id=platform_tenant.id,
            email=unique_email,
            role_name="platform_admin"
        )
        
        # Get a role to assign
        result = await db_session.execute(
            select(PlatformRole).where(PlatformRole.name == "support_staff")
        )
        support_role = result.scalar_one()
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=platform_tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            "/api/platform/invitations/",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={
                "email": invite_email,
                "role_id": str(support_role.id)
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert data["email"] == invite_email
        assert data["role_name"] == "support_staff"
        assert "token" in data
        assert "expires_at" in data

  
        # Verify invitation in database
        result = await db_session.execute(
            select(PlatformInvitation).where(PlatformInvitation.email == invite_email)
        )
        invitation = result.scalar_one()
        assert invitation is not None
        assert invitation.platform_role_id == support_role.id
        assert invitation.status.value == "pending"
    
    @pytest.mark.asyncio
    async def test_list_invitations_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test listing platform invitations"""
        unique_email = f"admin-{uuid4().hex[:8]}@platform.net"
        
        platform_tenant = await create_platform_tenant(db_session)
        admin = await create_platform_user(
            db_session,
            platform_tenant_id=platform_tenant.id,
            email=unique_email,
            role_name="platform_admin"
        )
        
        # Create an invitation first
        result = await db_session.execute(
            select(PlatformRole).where(PlatformRole.name == "billing_manager")
        )
        role = result.scalar_one()
        
        invitation = PlatformInvitation(
            email=f"test-{uuid4().hex[:8]}@platform.net",
            platform_role_id=role.id,
            token=uuid4().hex,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            invited_by=admin.id
        )
        db_session.add(invitation)
        await db_session.commit()
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=platform_tenant.firebase_tenant_id
        ))
        
        response = await api_client.get(
            "/api/platform/invitations/",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        invitations = response.json()
        
        assert isinstance(invitations, list)
        assert len(invitations) >= 1
        
        # Find our invitation
        our_invite = next((inv for inv in invitations if inv["email"] == invitation.email), None)
        assert our_invite is not None
        assert our_invite["status"] == "pending"
        assert our_invite["role_name"] == "billing_manager"
    
    @pytest.mark.asyncio
    async def test_revoke_invitation_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test revoking a platform invitation"""
        unique_email = f"admin-{uuid4().hex[:8]}@platform.net"
        
        platform_tenant = await create_platform_tenant(db_session)
        admin = await create_platform_user(
            db_session,
            platform_tenant_id=platform_tenant.id,
            email=unique_email,
            role_name="platform_admin"
        )
        
        # Create invitation to revoke
        result = await db_session.execute(
            select(PlatformRole).where(PlatformRole.name == "platform_admin")
        )
        role = result.scalar_one()
        
        invitation = PlatformInvitation(
            email=f"revoke-{uuid4().hex[:8]}@platform.net",
            platform_role_id=role.id,
            token=uuid4().hex,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            invited_by=admin.id
        )
        db_session.add(invitation)
        await db_session.commit()
        await db_session.refresh(invitation)
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=platform_tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            f"/api/platform/invitations/{invitation.id}/revoke",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        
        # Verify invitation status changed
        await db_session.refresh(invitation)
        assert invitation.status.value == "revoked"
    
    @pytest.mark.asyncio
    async def test_validate_invitation_token_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test validating a valid invitation token"""
        # Create invitation
        result = await db_session.execute(
            select(PlatformRole).where(PlatformRole.name == "support_staff")
        )
        role = result.scalar_one()
        
        platform_tenant = await create_platform_tenant(db_session)
        admin = await create_platform_user(
            db_session,
            platform_tenant_id=platform_tenant.id,
            email=f"admin-{uuid4().hex[:8]}@platform.net",
            role_name="platform_admin"
        )
        
        token = uuid4().hex
        invitation = PlatformInvitation(
            email=f"validate-{uuid4().hex[:8]}@platform.net",
            platform_role_id=role.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            invited_by=admin.id
        )
        db_session.add(invitation)
        await db_session.commit()
        
        # Validate token (public endpoint, no auth needed)
        response = await api_client.get(f"/api/platform/invitations/validate/{token}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == invitation.email
        assert data["role_name"] == "support_staff"
        assert data["is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_validate_expired_invitation_token(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that expired tokens are rejected"""
        result = await db_session.execute(
            select(PlatformRole).where(PlatformRole.name == "support_staff")
        )
        role = result.scalar_one()
        
        platform_tenant = await create_platform_tenant(db_session)
        admin = await create_platform_user(
            db_session,
            platform_tenant_id=platform_tenant.id,
            email=f"admin-{uuid4().hex[:8]}@platform.net",
            role_name="platform_admin"
        )
        
        token = uuid4().hex
        invitation = PlatformInvitation(
            email=f"expired-{uuid4().hex[:8]}@platform.net",
            platform_role_id=role.id,
            token=token,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired yesterday
            invited_by=admin.id
        )
        db_session.add(invitation)
        await db_session.commit()
        
        response = await api_client.get(f"/api/platform/invitations/validate/{token}")
        
        # Should fail (404 or 400)
        assert response.status_code in [400, 404]
    
    @pytest.mark.asyncio
    async def test_validate_invalid_token(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that invalid tokens are rejected"""
        fake_token = "nonexistent-token-12345"
        
        response = await api_client.get(f"/api/platform/invitations/validate/{fake_token}")
        
        assert response.status_code == 404
