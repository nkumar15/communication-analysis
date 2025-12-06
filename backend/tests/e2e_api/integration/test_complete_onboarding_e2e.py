"""
End-to-End Integration Tests for Complete Onboarding Journey

Tests the full production flow from platform admin creating a tenant
through owner activation and usage, including inviting other users.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from unittest.mock import patch

from services.b2b.models import TenantModel, UserModel, InvitationModel
from services.b2b.services.rls_service import rls_service
from core.constants import B2BRoleName
from tests.conftest import (
    create_test_user,
    create_mock_firebase_token,
    encode_mock_jwt,
    platform_admin_setup
)


@pytest.mark.integration
class TestCompleteOnboardingJourney:
    """Test complete tenant onboarding journey from start to finish"""
    
    @pytest.mark.asyncio
    async def test_complete_tenant_onboarding_journey(
        self,
        api_client: AsyncClient,
        platform_admin_setup,
        db_session: AsyncSession
    ):
        """
        Full integration test simulating real-world production flow:
        
        1. Platform admin logs in
        2. Platform admin creates tenant (onboards)
        3. Owner receives activation email (simulated)
        4. Owner validates activation token
        5. Owner performs SSO login (mocked Firebase)
        6. Owner completes activation
        7. Owner can now use B2B API endpoints
        8. Owner invites another user
        9. Invited user accepts invitation
        
        This test catches integration issues that unit tests miss.
        """
        platform_admin_token = platform_admin_setup["token"]
        
        # ====================
        # STEP 1-2: Platform Admin Onboards Tenant
        # ====================
        
        with patch('services.platform.services.tenant_onboarding_service.create_firebase_tenant') as mock_create_tenant, \
             patch('services.platform.services.tenant_onboarding_service.configure_oidc_provider') as mock_config_oidc:
            
            mock_create_tenant.return_value = f"test-tenant-{uuid4().hex[:8]}"
            mock_config_oidc.return_value = "oidc.test"
            
            domain = f"test-e2e-{uuid4().hex[:8]}.com"
            owner_email = f"owner@{domain}"
            
            print(f"\n=== STEP 1-2: Platform Admin Onboards Tenant ===")
            print(f"Domain: {domain}")
            print(f"Owner Email: {owner_email}")
            
            onboard_response = await api_client.post(
                "/api/platform/tenants/onboard",
                json={
                    "company_name": "E2E Test Corp",
                    "domain": domain,
                    "owner_email": owner_email,
                    "oidc_provider": "auth0",
                    "oidc_client_id": "test-client",
                    "oidc_client_secret": "test-secret",
                    "oidc_issuer": "https://test.auth0.com"
                },
                headers={"Authorization": f"Bearer {platform_admin_token}"}
            )
            
            assert onboard_response.status_code == 201
            onboard_data = onboard_response.json()
            tenant_id = onboard_data["tenant_id"]
            activation_token = onboard_data["activation_token"]
            
            print(f"✅ Tenant created with ID: {tenant_id}")
            print(f"✅ Activation token generated")
            
            # Verify tenant is pending
            tenant = await db_session.get(TenantModel, tenant_id)
            assert tenant.activation_status == "pending"
        
        # ====================
        # STEP 3-4: Owner Validates Activation Token
        # ====================
        
        print(f"\n=== STEP 3-4: Owner Validates Activation Token ===")
        
        validate_response = await api_client.get(
            f"/api/b2b/activation/validate/{activation_token}"
        )
        
        assert validate_response.status_code == 200
        validate_data = validate_response.json()
        assert validate_data["tenant_id"] == tenant_id
        assert validate_data["admin_email"] == owner_email
        print(f"✅ Activation token validated successfully")
        
        # Get tenant SSO configuration
        tenant_info_response = await api_client.get(
            f"/api/b2b/activation/tenant-info/{tenant_id}"
        )
        
        assert tenant_info_response.status_code == 200
        tenant_info = tenant_info_response.json()
        assert "firebase_tenant_id" in tenant_info
        print(f"✅ Tenant SSO configuration retrieved")
        
        # ====================
        # STEP 5: Owner Performs SSO Login (Simulated)
        # ====================
        
        print(f"\n=== STEP 5: Owner Performs SSO Login ===")
        
        firebase_uid = f"firebase-owner-{uuid4().hex[:8]}"
        
        # Create owner user (simulating what Firebase auth sync would do)
        await rls_service.set_tenant_context(db_session, tenant.id)
        owner_user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=owner_email,
            firebase_uid=firebase_uid,
            role_slug=B2BRoleName.OWNER
        )
        await db_session.commit()
        print(f"✅ Owner user created via SSO login simulation")
        
        # ====================
        # STEP 6: Owner Completes Activation
        # ====================
        
        print(f"\n=== STEP 6: Owner Completes Activation ===")
        
        owner_jwt = encode_mock_jwt(create_mock_firebase_token(
            uid=firebase_uid,
            email=owner_email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        complete_response = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {owner_jwt}"}
        )
        
        assert complete_response.status_code == 200
        complete_data = complete_response.json()
        assert complete_data["message"] == "Tenant activated successfully"
        print(f"✅ Tenant activation completed")
        
        # Verify tenant is now active
        await db_session.refresh(tenant)
        assert tenant.activation_status == "active"
        print(f"✅ Tenant status changed to 'active'")
        
        # ====================
        # STEP 7: Owner Uses B2B API Endpoints
        # ====================
        
        print(f"\n=== STEP 7: Owner Uses B2B API Endpoints ===")
        
        # List invitations
        list_invitations_response = await api_client.get(
            "/api/b2b/invitations/list",
            headers={"Authorization": f"Bearer {owner_jwt}"}
        )
        
        assert list_invitations_response.status_code == 200
        invitations = list_invitations_response.json()
        print(f"✅ Owner can access invitations endpoint")
        print(f"   Found {len(invitations)} invitation(s)")
        
        # ====================
        # STEP 8: Owner Invites Another User
        # ====================
        
        print(f"\n=== STEP 8: Owner Invites Another User ===")
        
        invited_email = f"user@{domain}"
        
        invite_response = await api_client.post(
            "/api/b2b/invitations/invite",
            json={
                "email": invited_email,
                "role": B2BRoleName.VIEWER,
                "team_id": None,
                "team_role": None
            },
            headers={"Authorization": f"Bearer {owner_jwt}"}
        )
        
        assert invite_response.status_code == 200
        invite_data = invite_response.json()
        invitation_id = invite_data["invitation_id"]
        print(f"✅ Owner invited new user: {invited_email}")
        
        # Query database for invitation token (not returned in API response)
        await rls_service.set_tenant_context(db_session, tenant.id)
        from sqlalchemy import select
        from services.b2b.models import InvitationModel
        
        invitation_result = await db_session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        invitation = invitation_result.scalar_one()
        invitation_token = invitation.invitation_token
        print(f"   Invitation token: {invitation_token[:20]}...")
        
        # ====================
        # STEP 9: Invited User Accepts Invitation
        # ====================
        
        print(f"\n=== STEP 9: Invited User Accepts Invitation ===")
        
        # Validate invitation
        validate_invite_response = await api_client.get(
            f"/api/b2b/invitations/accept/{invitation_token}"
        )
        
        assert validate_invite_response.status_code == 200
        validate_invite_data = validate_invite_response.json()
        assert validate_invite_data["email"] == invited_email
        print(f"✅ Invitation token validated")
        
        # Simulate invited user SSO login
        invited_firebase_uid = f"firebase-user-{uuid4().hex[:8]}"
        
        invited_jwt = encode_mock_jwt(create_mock_firebase_token(
            uid=invited_firebase_uid,
            email=invited_email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Accept invitation
        accept_response = await api_client.post(
            f"/api/b2b/invitations/join?token={invitation_token}",
            headers={"Authorization": f"Bearer {invited_jwt}"}
        )
        
        assert accept_response.status_code == 200
        accept_data = accept_response.json()
        # Join endpoint returns message, tenant_id, role, team_id
        assert accept_data["message"] == "Successfully joined tenant"
        assert accept_data["role"] == B2BRoleName.VIEWER
        print(f"✅ Invitation accepted successfully")
        print(f"   Assigned role: {accept_data['role']}")
        
        # ====================
        # VERIFICATION: Check Final State
        # ====================
        
        print(f"\n=== FINAL VERIFICATION ===")
        
        # Verify tenant has 2 users now
        await rls_service.set_tenant_context(db_session, tenant.id)
        from sqlalchemy import select, func
        user_count_result = await db_session.execute(
            select(func.count()).select_from(UserModel).where(
                UserModel.tenant_id == tenant.id
            )
        )
        user_count = user_count_result.scalar()
        assert user_count == 2  # Owner + invited user
        print(f"✅ Tenant now has {user_count} users")
        
        # Verify invitation was marked as accepted
        invitation_result = await db_session.execute(
            select(InvitationModel).where(
                InvitationModel.invitation_token == invitation_token
            )
        )
        invitation = invitation_result.scalar_one()
        assert invitation.accepted_at is not None
        print(f"✅ Invitation marked as accepted")
        
        # Verify both users can access their endpoints
        owner_me_response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {owner_jwt}"}
        )
        assert owner_me_response.status_code == 200
        
        invited_me_response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {invited_jwt}"}
        )
        assert invited_me_response.status_code == 200
        print(f"✅ Both users can access their endpoints")
        
        print(f"\n=== END-TO-END TEST COMPLETE ===")
        print(f"✅ ALL STEPS PASSED!")
