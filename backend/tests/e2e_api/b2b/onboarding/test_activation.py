"""
Integration tests for tenant activation flow

Scope:
- Happy Path (Full process)
- Error Reporting (Invalid tokens, bad inputs)
- Security (Replay attacks, unauthorized access)
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from services.b2b.models import UserModel, TenantModel, InvitationModel
from core.rls import rls_service
from core.constants import B2BRoleName
from datetime import datetime, timedelta, timezone
import secrets
from unittest.mock import patch
from uuid import uuid4

from tests.conftest import (
    create_test_tenant,
    create_test_user,
    create_test_invitation,
    create_mock_firebase_token,
    encode_mock_jwt,
    platform_admin_setup
)


@pytest.mark.integration
class TestActivationFlow:
    """Test complete tenant activation workflow (Happy Path)"""
    
    @pytest.mark.asyncio
    async def test_complete_activation_success_path(
        self,
        api_client: AsyncClient,
        platform_admin_setup,
        db_session: AsyncSession
    ):
        """
        Test complete activation flow: Platform creates → Owner activates → Tenant active
        """
        platform_admin_token = platform_admin_setup["token"]
        
        # Mock Firebase interactions for onboarding
        with patch('services.platform.services.tenant_onboarding_service.create_firebase_tenant') as mock_create_tenant, \
             patch('services.platform.services.tenant_onboarding_service.configure_oidc_provider') as mock_config_oidc:
            
            mock_create_tenant.return_value = f"test-tenant-{uuid4().hex[:8]}"
            mock_config_oidc.return_value = "oidc.test"
            
            # Step 1: Platform admin creates tenant
            domain = f"test-complete-{uuid4().hex[:8]}.com"
            owner_email = f"owner@{domain}"
            
            onboard_response = await api_client.post(
                "/api/platform/b2b/tenants/onboard",
                json={
                    "company_name": "Test Corp",
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
            
            # Verify tenant created with pending status
            tenant = await db_session.get(TenantModel, tenant_id)
            assert tenant.activation_status == "pending"
        
        # Step 2: Owner validates activation token
        validate_response = await api_client.get(
            f"/api/b2b/activation/validate/{activation_token}"
        )
        
        assert validate_response.status_code == 200
        validate_data = validate_response.json()
        assert validate_data["tenant_id"] == tenant_id
        assert validate_data["admin_email"] == owner_email
        
        # Step 3: Owner gets tenant SSO configuration
        tenant_info_response = await api_client.get(
            f"/api/b2b/activation/tenant-info/{tenant_id}"
        )
        
        assert tenant_info_response.status_code == 200
        tenant_info = tenant_info_response.json()
        assert "firebase_tenant_id" in tenant_info
        
        # Step 4: Owner performs SSO login (mocked) - this creates the user
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        
        # Create owner user (simulating what auth sync would do)
        await rls_service.set_tenant_context(db_session, tenant.id)
        owner_user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=owner_email,
            firebase_uid=firebase_uid,
            role_slug=B2BRoleName.OWNER
        )
        await db_session.commit()
        
        # Step 5: Owner completes activation
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
        
        # Step 6: Verify tenant is now active
        await db_session.refresh(tenant)
        assert tenant.activation_status == "active"
        
        # Step 7: Verify invitation was accepted
        await rls_service.set_tenant_context(db_session, tenant.id)
        invitation_result = await db_session.execute(
            select(InvitationModel).where(
                InvitationModel.tenant_id == tenant.id,
                InvitationModel.email == owner_email
            )
        )
        invitation = invitation_result.scalar_one()
        assert invitation.accepted_at is not None

    @pytest.mark.asyncio
    async def test_validate_activation_token_success(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test /api/b2b/activation/validate with valid token returns correct data"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        activation_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=2)
        
        await db_session.execute(
            update(TenantModel).where(TenantModel.id == tenant.id).values(
                activation_token=activation_token,
                activation_expires_at=expires_at
            )
        )
        
        await rls_service.set_tenant_context(db_session, tenant.id)
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=f"owner@{tenant.domain}",
            role=B2BRoleName.OWNER
        )
        invitation.invitation_token = activation_token
        await db_session.commit()
        
        response = await api_client.get(f"/api/b2b/activation/validate/{activation_token}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(tenant.id)
        assert data["admin_email"] == f"owner@{tenant.domain}"

    @pytest.mark.asyncio
    async def test_get_tenant_info_for_activation(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test /api/b2b/activation/tenant-info returns Firebase configuration"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        await db_session.commit()
        
        response = await api_client.get(f"/api/b2b/activation/tenant-info/{tenant.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(tenant.id)
        assert "firebase_tenant_id" in data

    @pytest.mark.asyncio
    async def test_check_activation_status_pending(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test status check before owner logs in returns 'pending'"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        activation_token = secrets.token_urlsafe(32)
        await db_session.execute(update(TenantModel).where(TenantModel.id == tenant.id).values(activation_token=activation_token))
        
        # We must create an invitation, otherwise check-status returns "invalid"
        await rls_service.set_tenant_context(db_session, tenant.id)
        owner_email = f"owner@{tenant.domain}"
        invitation = await create_test_invitation(db_session, tenant_id=tenant.id, email=owner_email, role=B2BRoleName.OWNER)
        invitation.invitation_token = activation_token
        await db_session.commit()
        
        response = await api_client.get(f"/api/b2b/activation/check-status/{activation_token}")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_check_activation_status_ready(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test status check after owner user created returns 'ready'"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        activation_token = secrets.token_urlsafe(32)
        await db_session.execute(update(TenantModel).where(TenantModel.id == tenant.id).values(activation_token=activation_token))
        
        await rls_service.set_tenant_context(db_session, tenant.id)
        owner_email = f"owner@{tenant.domain}"
        await create_test_user(db_session, tenant_id=tenant.id, email=owner_email, role_slug=B2BRoleName.OWNER)
        
        # Create invitation to link token to email (implied dependency)
        invitation = await create_test_invitation(db_session, tenant_id=tenant.id, email=owner_email, role=B2BRoleName.OWNER)
        invitation.invitation_token = activation_token
        await db_session.commit()

        response = await api_client.get(f"/api/b2b/activation/check-status/{activation_token}")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    @pytest.mark.asyncio
    async def test_activation_sets_rls_context(self, api_client: AsyncClient, db_session: AsyncSession):
        """Verify RLS context management during activation helpers (Unitish)"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        # Ensure context clear
        await rls_service.clear_context(db_session)
        assert await rls_service.get_current_context(db_session) is None
        
        # Set context
        await rls_service.set_tenant_context(db_session, tenant.id)
        assert await rls_service.get_current_context(db_session) == tenant.id


@pytest.mark.integration
class TestActivationErrors:
    """Test error cases in activation flow (validation, expired tokens, wrong users)"""
    
    @pytest.mark.asyncio
    async def test_activation_with_invalid_token(self, api_client: AsyncClient):
        """Test that activation fails with nonexistent/invalid token"""
        fake_token = secrets.token_urlsafe(32)
        response = await api_client.get(f"/api/b2b/activation/validate/{fake_token}")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_activation_with_expired_token(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test that activation fails with expired token"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        activation_token = secrets.token_urlsafe(32)
        
        # Set expiry to PAST
        await db_session.execute(
            update(TenantModel).where(TenantModel.id == tenant.id).values(
                activation_token=activation_token,
                activation_expires_at=datetime.now(timezone.utc) - timedelta(days=1)
            )
        )
        await db_session.commit()
        
        response = await api_client.get(f"/api/b2b/activation/validate/{activation_token}")
        assert response.status_code == 410  # Gone

    @pytest.mark.asyncio
    async def test_activation_with_wrong_email(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test that activation fails when user email doesn't match invitation"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        activation_token = secrets.token_urlsafe(32)
        
        await db_session.execute(
            update(TenantModel).where(TenantModel.id == tenant.id).values(
                activation_token=activation_token,
                activation_expires_at=datetime.now(timezone.utc) + timedelta(days=2)
            )
        )
        
        await rls_service.set_tenant_context(db_session, tenant.id)
        # Create invitation for CORRECT email
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=f"owner@{tenant.domain}",
            role=B2BRoleName.OWNER
        )
        invitation.invitation_token = activation_token
        
        # Create user with WRONG email
        wrong_email = f"hacker@{tenant.domain}"
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=wrong_email,
            firebase_uid=firebase_uid,
            role_slug=B2BRoleName.OWNER
        )
        await db_session.commit()
        
        wrong_jwt = encode_mock_jwt(create_mock_firebase_token(
            uid=firebase_uid, email=wrong_email, firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {wrong_jwt}"}
        )
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_activation_with_non_owner_role(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test that non-owner user cannot activate tenant"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        activation_token = secrets.token_urlsafe(32)
        
        await db_session.execute(update(TenantModel).where(TenantModel.id == tenant.id).values(
            activation_token=activation_token,
            activation_expires_at=datetime.now(timezone.utc) + timedelta(days=2)
        ))
        
        await rls_service.set_tenant_context(db_session, tenant.id)
        email = f"viewer@{tenant.domain}"
        invitation = await create_test_invitation(db_session, tenant_id=tenant.id, email=email, role=B2BRoleName.VIEWER)
        invitation.invitation_token = activation_token
        
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        await create_test_user(db_session, tenant_id=tenant.id, email=email, firebase_uid=firebase_uid, role_slug=B2BRoleName.VIEWER)
        await db_session.commit()
        
        jwt = encode_mock_jwt(create_mock_firebase_token(uid=firebase_uid, email=email, firebase_tenant_id=tenant.firebase_tenant_id))
        
        response = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {jwt}"}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_pending_tenant_users_cannot_access_b2b_endpoints(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test users in pending tenants are blocked from APIs"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        await rls_service.set_tenant_context(db_session, tenant.id)
        
        email = f"user@{tenant.domain}"
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        user = await create_test_user(db_session, tenant_id=tenant.id, email=email, firebase_uid=firebase_uid, role_slug=B2BRoleName.OWNER)
        await db_session.commit()
        
        jwt = encode_mock_jwt(create_mock_firebase_token(uid=firebase_uid, email=email, firebase_tenant_id=tenant.firebase_tenant_id))
        
        response = await api_client.get("/api/b2b/invitations/list", headers={"Authorization": f"Bearer {jwt}"})
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_activation_without_invitation(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test validation fails if no invitation exists for the token"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        activation_token = secrets.token_urlsafe(32)
        await db_session.execute(update(TenantModel).where(TenantModel.id == tenant.id).values(activation_token=activation_token))
        await db_session.commit()
        
        response = await api_client.get(f"/api/b2b/activation/validate/{activation_token}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_concurrent_activation_prevented(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test concurrent activation prevented by activation_started_at"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        activation_token = secrets.token_urlsafe(32)
        
        await db_session.execute(update(TenantModel).where(TenantModel.id == tenant.id).values(
            activation_token=activation_token,
            activation_started_at=datetime.now(timezone.utc) - timedelta(minutes=30)
        ))
        
        await rls_service.set_tenant_context(db_session, tenant.id)
        email = f"owner@{tenant.domain}"
        invitation = await create_test_invitation(db_session, tenant_id=tenant.id, email=email, role=B2BRoleName.OWNER)
        invitation.invitation_token = activation_token
        
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        await create_test_user(db_session, tenant_id=tenant.id, email=email, firebase_uid=firebase_uid, role_slug=B2BRoleName.OWNER)
        await db_session.commit()
        
        jwt = encode_mock_jwt(create_mock_firebase_token(uid=firebase_uid, email=email, firebase_tenant_id=tenant.firebase_tenant_id))
        
        response = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {jwt}"}
        )
        assert response.status_code == 409


@pytest.mark.integration
class TestActivationSecurity:
    """Test tenant activation security scenarios (Replay Attacks)"""

    @pytest.mark.asyncio
    async def test_activation_replay_attack_prevented(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test that token cannot be reused after first activation"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        activation_token = secrets.token_urlsafe(32)
        
        await db_session.execute(
            update(TenantModel).where(TenantModel.id == tenant.id).values(
                activation_token=activation_token,
                activation_expires_at=datetime.now(timezone.utc) + timedelta(days=2)
            )
        )
        
        await rls_service.set_tenant_context(db_session, tenant.id)
        owner_email = f"owner@{tenant.domain}"
        
        # Create invitation
        invitation = await create_test_invitation(
            db_session, tenant_id=tenant.id, email=owner_email, role=B2BRoleName.OWNER
        )
        invitation.invitation_token = activation_token
        
        # Create user
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        await create_test_user(
            db_session, tenant_id=tenant.id, email=owner_email, 
            firebase_uid=firebase_uid, role_slug=B2BRoleName.OWNER
        )
        await db_session.commit()
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=firebase_uid, email=owner_email, firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # 1. Activate successfully
        response1 = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response1.status_code == 200
        
        # 2. REPLAY: Try again
        response2 = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response2.status_code in [404, 409]

    @pytest.mark.asyncio
    async def test_double_activation_prevented(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test that validation fails if tenant already active"""
        tenant = await create_test_tenant(db_session, activation_status="active")
        activation_token = secrets.token_urlsafe(32)
        
        await db_session.execute(
            update(TenantModel).where(TenantModel.id == tenant.id).values(activation_token=activation_token)
        )
        await db_session.commit()
        
        response = await api_client.get(f"/api/b2b/activation/validate/{activation_token}")
        assert response.status_code == 400
        assert "already activated" in response.json()["detail"].lower()
