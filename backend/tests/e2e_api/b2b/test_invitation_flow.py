"""
Integration tests for invitation flow
Tests all scenarios: create, validate, accept, cancel, resend
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from services.b2b.models import InvitationModel, TenantModel, UserModel
from core.config import settings
from core.constants import B2BRoleName
from uuid import UUID

from tests.conftest import (
    create_mock_firebase_token,
    encode_mock_jwt,
    create_test_tenant,
    create_test_user,
    create_test_invitation
)


@pytest.mark.integration
class TestInvitationFlow:
    """Test invitation creation, validation, and acceptance"""
    
    @pytest.mark.asyncio
    async def test_owner_invites_admin_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Owner successfully invites an admin"""
        # Setup: Create tenant and owner user
        tenant = await create_test_tenant(db_session)
        owner = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        # Create mock JWT for owner
        jwt_payload = create_mock_firebase_token(
            uid=owner.firebase_uid,
            email=owner.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        )
        jwt_token = encode_mock_jwt(jwt_payload)
        
        # Send invitation
        response = await api_client.post(
            "/api/b2b/invitations/invite",
            json={"email": f"newadmin@{tenant.domain}", "role": B2BRoleName.ADMIN},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == f"newadmin@{tenant.domain}"
        assert data["status"] == "sent"
        assert "invitation_id" in data
    
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_invite_users(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Viewer cannot invite users (missing permissions)"""
        tenant = await create_test_tenant(db_session)
        viewer = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"viewer@{tenant.domain}",
            role_slug=B2BRoleName.VIEWER
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=viewer.firebase_uid,
            email=viewer.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            "/api/b2b/invitations/invite",
            json={"email": f"user@{tenant.domain}", "role": B2BRoleName.VIEWER},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 403
        # The error message comes from the permission checker dependency
        assert "You do not have permission" in response.json()["detail"]
    
    
    @pytest.mark.asyncio
    async def test_email_domain_mismatch_rejected(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Invitation to wrong domain is rejected"""
        from uuid import uuid4
        domain = f"company-{uuid4().hex[:8]}.com" # Random domain to avoid collision
        tenant = await create_test_tenant(db_session, domain=domain)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            "/api/b2b/invitations/invite",
            json={"email": "user@different.com", "role": B2BRoleName.VIEWER},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 400
        assert "Email domain must match tenant domain" in response.json()["detail"]
    
    
    @pytest.mark.asyncio
    async def test_validate_invitation_pii_minimization(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Validation endpoint returns minimal PII"""
        tenant = await create_test_tenant(db_session)
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=f"user@{tenant.domain}",
            role=B2BRoleName.VIEWER
        )
        
        response = await api_client.get(
            f"/api/b2b/invitations/accept/{invitation.invitation_token}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check PII minimization - should NOT contain these
        assert "inviter_name" not in data
        
        # Should contain these
        assert data["email"] == f"user@{tenant.domain}"
        assert data["tenant_name"] == tenant.name
        assert "tenant_id" not in data  # PII minimization check
        assert data["role"] == B2BRoleName.VIEWER
    
    
    @pytest.mark.asyncio
    async def test_accept_invitation_with_verified_email_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """User with verified email can accept invitation"""
        tenant = await create_test_tenant(db_session)
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=f"newuser@{tenant.domain}",
            role=B2BRoleName.VIEWER
        )
        
        # Mock JWT with verified email
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid="new-user-firebase-uid",
            email=f"newuser@{tenant.domain}",
            email_verified=True,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            f"/api/b2b/invitations/join?token={invitation.invitation_token}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully joined tenant"
        
        # Verify audit trail
        from services.b2b.models import InvitationModel
        from sqlalchemy import select
        
        result = await db_session.execute(
            select(InvitationModel).where(
                InvitationModel.invitation_token == invitation.invitation_token
            )
        )
        updated_invitation = result.scalar_one()
        
        assert updated_invitation.accepted_at is not None
        assert updated_invitation.accepted_by is not None
        assert updated_invitation.accepted_from_ip is not None
    
    
    @pytest.mark.asyncio
    async def test_accept_invitation_with_unverified_email_rejected(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """User with unverified email CANNOT accept invitation (security fix)"""
        tenant = await create_test_tenant(db_session)
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=f"unverified@{tenant.domain}",
            role=B2BRoleName.VIEWER
        )
        
        # Mock JWT with UNverified email
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid="unverified-user",
            email=f"unverified@{tenant.domain}",
            email_verified=False,  # NOT VERIFIED
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            f"/api/b2b/invitations/join?token={invitation.invitation_token}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 403
        assert "Email must be verified" in response.json()["detail"]
    
    
    @pytest.mark.asyncio
    async def test_duplicate_pending_invitation_rejected(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Cannot create duplicate pending invitation"""
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        # Create existing invitation
        await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=f"user@{tenant.domain}",
            role=B2BRoleName.VIEWER
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Try to create duplicate
        response = await api_client.post(
            "/api/b2b/invitations/invite",
            json={"email": f"user@{tenant.domain}", "role": B2BRoleName.VIEWER},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 400
        assert "Pending invitation already exists" in response.json()["detail"]
    
    
    @pytest.mark.asyncio
    async def test_invite_with_team_assignment_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Admin can invite user with team assignment"""
        from services.b2b.models import Team
        
        # Setup: Create tenant, admin, and team
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        # Create a team
        team = Team(
            tenant_id=tenant.id,
            name="Engineering",
            description="Engineering team",
            is_default=False,
            created_by=admin.id
        )
        db_session.add(team)
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Send invitation with team assignment
        response = await api_client.post(
            "/api/b2b/invitations/invite",
            json={
                "email": f"newuser@{tenant.domain}",
                "role": B2BRoleName.VIEWER,
                "team_id": str(team.id),
                "team_role": "team_contributor"
            },
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == f"newuser@{tenant.domain}"
        assert data["team_id"] == str(team.id)
        
        # Verify invitation saved with team_role
        result = await db_session.execute(
            select(InvitationModel).where(
                InvitationModel.email == f"newuser@{tenant.domain}"
            )
        )
        invitation = result.scalar_one()
        assert invitation.team_id == team.id
        assert invitation.team_role == "team_contributor"
    
    
    @pytest.mark.asyncio
    async def test_accept_invitation_auto_adds_to_team(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """User accepting invitation is auto-added to specified team with team role"""
        from services.b2b.models import Team, TeamMember
        
        # Setup
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        # Create team
        team = Team(
            tenant_id=tenant.id,
            name="Marketing",
            description="Marketing team",
            is_default=False,
            created_by=admin.id
        )
        db_session.add(team)
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)
        
        # Create invitation with team assignment
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=f"newuser@{tenant.domain}",
            role=B2BRoleName.VIEWER,
            team_id=team.id,
            team_role="team_manager"
        )
        
        # Accept invitation
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid="new-user-uid",
            email=f"newuser@{tenant.domain}",
            email_verified=True,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            f"/api/b2b/invitations/join?token={invitation.invitation_token}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        
        # Verify user was added to team with correct role
        result = await db_session.execute(
            select(UserModel).where(
                UserModel.email == f"newuser@{tenant.domain}"
            )
        )
        user = result.scalar_one()
        
        # Check team membership
        member_result = await db_session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.id,
                TeamMember.user_id == user.id
            )
        )
        team_member = member_result.scalar_one()
        
        assert team_member.team_role == "team_manager"
    
    
    @pytest.mark.asyncio
    async def test_invite_without_team_adds_to_default_team(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """User invited without team assignment is added to default team"""
        from services.b2b.models import Team, TeamMember
        
        # Setup - create_test_tenant already creates a default team
        tenant = await create_test_tenant(db_session)
        
        # Get the default team (created by create_test_tenant)
        result = await db_session.execute(
            select(Team).where(
                Team.tenant_id == tenant.id,
                Team.is_default == True
            )
        )
        default_team = result.scalar_one()
        
        # Create invitation without team assignment
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=f"newuser@{tenant.domain}",
            role=B2BRoleName.VIEWER
        )
        
        # Accept invitation
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid="new-user-uid",
            email=f"newuser@{tenant.domain}",
            email_verified=True,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            f"/api/b2b/invitations/join?token={invitation.invitation_token}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        
        # Verify user was added to default team
        result = await db_session.execute(
            select(UserModel).where(
                UserModel.email == f"newuser@{tenant.domain}"
            )
        )
        user = result.scalar_one()
        
        # Check team membership
        member_result = await db_session.execute(
            select(TeamMember).where(
                TeamMember.team_id == default_team.id,
                TeamMember.user_id == user.id
            )
        )
        team_member = member_result.scalar_one()
        
        assert team_member.team_role == "team_contributor"  # Default role

