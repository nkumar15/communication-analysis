"""
Integration tests for invitation flow
Tests all scenarios: create, validate, accept, cancel, resend
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from modules.b2b.models import InvitationModel, TenantModel, UserModel
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
        from modules.b2b.models import InvitationModel
        from sqlalchemy import select
        from tests.conftest import set_tenant_context
        
        # Re-set RLS context as it might be lost after app commit
        await set_tenant_context(db_session, tenant.id)
        
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
        from modules.b2b.models import Team
        
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
        from tests.conftest import set_tenant_context
        await set_tenant_context(db_session, tenant.id)
        
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
        from modules.b2b.models import Team, TeamMember
        
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
        from tests.conftest import set_tenant_context
        await set_tenant_context(db_session, tenant.id)
        
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
    async def test_invite_without_team_creates_no_team_membership(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        User invited without team assignment has ZERO team memberships.
        
        This validates the "No default team" design principle:
        - No __unassigned__ team pattern
        - Empty team list is the valid unassigned state
        - User can login but has no business data access
        """
        from modules.b2b.models import TeamMember
        from sqlalchemy import func
        
        # Setup
        tenant = await create_test_tenant(db_session)
        
        # Create invitation WITHOUT team assignment
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=f"newuser@{tenant.domain}",
            role=B2BRoleName.MEMBER  # Default safe role
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
        
        # Verify user was created
        from tests.conftest import set_tenant_context
        await set_tenant_context(db_session, tenant.id)
        
        result = await db_session.execute(
            select(UserModel).where(
                UserModel.email == f"newuser@{tenant.domain}"
            )
        )
        user = result.scalar_one()
        
        # CRITICAL CHECK: User should have ZERO team memberships
        # This validates "No default team" design principle
        member_count_result = await db_session.execute(
            select(func.count()).select_from(TeamMember).where(
                TeamMember.user_id == user.id
            )
        )
        team_membership_count = member_count_result.scalar()
        
        assert team_membership_count == 0, (
            f"Expected 0 team memberships for user without team assignment, "
            f"got {team_membership_count}. "
            "This violates the 'No default team' design principle."
        )


    @pytest.mark.asyncio
    async def test_accept_invitation_assigns_correct_role(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Accepted invitation assigns the CORRECT role (Regression Fix)"""
        from modules.b2b.models import Role
        
        # Setup
        tenant = await create_test_tenant(db_session)
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=f"futureadmin@{tenant.domain}",
            role=B2BRoleName.ADMIN
        )
        
        # Accept
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid="future-admin-uid",
            email=f"futureadmin@{tenant.domain}",
            email_verified=True,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            f"/api/b2b/invitations/join?token={invitation.invitation_token}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response.status_code == 200
        
        # Verify Role
        from tests.conftest import set_tenant_context
        await set_tenant_context(db_session, tenant.id)
        
        result = await db_session.execute(
            select(UserModel).where(UserModel.email == f"futureadmin@{tenant.domain}")
        )
        user = result.scalar_one()
        
        # Check that role_id corresponds to ADMIN, not viewer
        # We need to fetch the role name for this role_id
        role_result = await db_session.execute(
            select(Role).where(Role.id == user.role_id)
        )
        role = role_result.scalar_one()
        
        assert role.name == B2BRoleName.ADMIN
        assert role.name != B2BRoleName.VIEWER


    
    @pytest.mark.asyncio
    async def test_invitation_system_role_validation_logic(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test case to validate System Role assignment logic during invitation.
        
        Objective:
        - Ensure that when a user is invited WITHOUT specifying a role, 
          the System Role defaults to 'member' (not 'viewer').
        - Verify that Team Role and System Role are independent layers.
        
        Scenarios:
        1. Single User Invite (API): Defaults to 'member' if 'role' field is omitted
        2. Invitation with only team_id/team_role should still default System Role to 'member'
        """
        # Setup: Create tenant and admin user
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        # Create JWT token
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Scenario 1: Invite user WITHOUT specifying role (should default to MEMBER)
        response = await api_client.post(
            "/api/b2b/invitations/invite",
            json={
                "email": f"newuser@{tenant.domain}",
                # "role" is intentionally omitted
            },
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        # NOTE: Endpoint returns 200 OK, not 201 Created (existing behavior)
        assert response.status_code == 200
        data = response.json()
        
        # API response doesn't include 'role' field, but we can verify email
        assert data["email"] == f"newuser@{tenant.domain}"
        assert data["status"] == "sent"
        
        # Set RLS context for DB queries
        from tests.conftest import set_tenant_context
        await set_tenant_context(db_session, tenant.id)
        
        # Verify in DB that the invitation was created with MEMBER role (not VIEWER)
        from modules.b2b.models import InvitationModel
        result = await db_session.execute(
            select(InvitationModel).where(
                InvitationModel.email == f"newuser@{tenant.domain}",
                InvitationModel.tenant_id == tenant.id
            )
        )
        invitation = result.scalar_one()
        assert invitation.role == B2BRoleName.MEMBER
        
        # Scenario 2: Invite user with team assignment but no System Role
        # Create a team first
        from modules.b2b.services.team_service import create_team
        team = await create_team(
            db=db_session,
            tenant_id=tenant.id,
            name="Engineering",
            description="Engineering team"
        )
        
        response2 = await api_client.post(
            "/api/b2b/invitations/invite",
            json={
                "email": f"engineer@{tenant.domain}",
                "team_id": str(team.id),
                "team_role": "team_contributor"
                # "role" is intentionally omitted
            },
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        # NOTE: Endpoint returns 200 OK, not 201 Created  (existing behavior)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # API response doesn't include role/team_role, verify from database
        assert data2["email"] == f"engineer@{tenant.domain}"
        assert data2["status"] == "sent"
        assert data2["team_id"] == str(team.id)
        
        # Verify System Role still defaults to MEMBER (independent of Team Role) - from DB
        result2 = await db_session.execute(
            select(InvitationModel).where(
                InvitationModel.email == f"engineer@{tenant.domain}",
                InvitationModel.tenant_id == tenant.id
            )
        )
        invitation2 = result2.scalar_one()
        assert invitation2.role == B2BRoleName.MEMBER
        assert invitation2.team_id == team.id
        assert invitation2.team_role == "team_contributor"


