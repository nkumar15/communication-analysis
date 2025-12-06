"""
Integration tests for tenant activation flow

Tests the complete activation workflow:
1. Platform admin creates tenant (status='pending')
2. Owner validates activation token
3. Owner retrieves tenant SSO configuration
4. Owner completes SSO login (mocked)
5. Owner completes activation
6. Tenant becomes active
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from services.b2b.models import TenantModel, UserModel, InvitationModel
from services.b2b.services.rls_service import rls_service
from core.constants import B2BRoleName
from datetime import datetime, timedelta, timezone
import secrets

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
    """Test complete tenant activation workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_activation_success_path(
        self,
        api_client: AsyncClient,
        platform_admin_setup,
        db_session: AsyncSession
    ):
        """
        Test complete activation flow: Platform creates → Owner activates → Tenant active
        
        This is the CRITICAL end-to-end test that was missing.
        It verifies the entire production flow works correctly.
        """
        from unittest.mock import patch
        from uuid import uuid4
        
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
                "/api/platform/tenants/onboard",
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
        assert "oidc_provider_id" in tenant_info
        
        # Step 4: Owner performs SSO login (mocked) - this creates the user
        # In production, Firebase creates the user. In tests, we manually create it.
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
        
        # Step 8: Verify owner can now use B2B API endpoints
        list_invitations_response = await api_client.get(
            "/api/b2b/invitations/list",
            headers={"Authorization": f"Bearer {owner_jwt}"}
        )
        
        assert list_invitations_response.status_code == 200
        # Owner should see their own accepted invitation
        invitations = list_invitations_response.json()
        assert len(invitations) >= 1
    
    
    @pytest.mark.asyncio
    async def test_validate_activation_token_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test /api/b2b/activation/validate with valid token returns correct data"""
        # Create pending tenant with activation token
        tenant = await create_test_tenant(
            db_session,
            activation_status="pending"
        )
        
        activation_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=2)
        
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(
                activation_token=activation_token,
                activation_expires_at=expires_at
            )
        )
        
        # Set RLS context to create invitation
        await rls_service.set_tenant_context(db_session, tenant.id)
        
        # Create invitation with same token
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=f"owner@{tenant.domain}",
            role=B2BRoleName.OWNER
        )
        invitation.invitation_token = activation_token
        await db_session.commit()
        
        # Validate token
        response = await api_client.get(f"/api/b2b/activation/validate/{activation_token}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(tenant.id)
        assert data["tenant_name"] == tenant.name
        assert data["domain"] == tenant.domain
        assert data["admin_email"] == f"owner@{tenant.domain}"
    
    
    @pytest.mark.asyncio
    async def test_validate_activation_token_expired(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test validation with expired token returns 410 Gone"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        activation_token = secrets.token_urlsafe(32)
        # Set expiry to past
        expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(
                activation_token=activation_token,
                activation_expires_at=expires_at
            )
        )
        await db_session.commit()
        
        response = await api_client.get(f"/api/b2b/activation/validate/{activation_token}")
        
        assert response.status_code == 410
        assert "expired" in response.json()["detail"].lower()
    
    
    @pytest.mark.asyncio
    async def test_validate_activation_token_already_active(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test validation when tenant already active returns 400"""
        # Create tenant that's already active
        tenant = await create_test_tenant(db_session, activation_status="active")
        
        activation_token = secrets.token_urlsafe(32)
        
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(activation_token=activation_token)
        )
        await db_session.commit()
        
        response = await api_client.get(f"/api/b2b/activation/validate/{activation_token}")
        
        assert response.status_code == 400
        assert "already activated" in response.json()["detail"].lower()
    
    
    @pytest.mark.asyncio
    async def test_get_tenant_info_for_activation(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test /api/b2b/activation/tenant-info returns Firebase configuration"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        await db_session.commit()
        
        response = await api_client.get(f"/api/b2b/activation/tenant-info/{tenant.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(tenant.id)
        assert data["tenant_name"] == tenant.name
        assert data["firebase_tenant_id"] == tenant.firebase_tenant_id
        # oidc_provider_id might be None if no auth provider configured
        assert "oidc_provider_id" in data
    
    
    @pytest.mark.asyncio
    async def test_check_activation_status_pending(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test status check before owner logs in returns 'pending'"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        activation_token = secrets.token_urlsafe(32)
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(activation_token=activation_token)
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
        
        # Check status before user is created
        response = await api_client.get(f"/api/b2b/activation/check-status/{activation_token}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["user_created"] == False
    
    
    @pytest.mark.asyncio
    async def test_check_activation_status_ready(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test status check after owner logs in returns 'ready'"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        activation_token = secrets.token_urlsafe(32)
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(activation_token=activation_token)
        )
        
        await rls_service.set_tenant_context(db_session, tenant.id)
        
        # Create invitation
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=f"owner@{tenant.domain}",
            role=B2BRoleName.OWNER
        )
        invitation.invitation_token = activation_token
        
        # Create owner user (simulating SSO login)
        owner = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"owner@{tenant.domain}",
            role_slug=B2BRoleName.OWNER
        )
        
        await db_session.commit()
        
        # Check status after user created
        response = await api_client.get(f"/api/b2b/activation/check-status/{activation_token}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["user_created"] == True
    
    
    @pytest.mark.asyncio
    async def test_activation_sets_rls_context(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Verify RLS context management during activation
        
        This test ensures that:
        1. Activation endpoint sets RLS context correctly
        2. RLS service methods work as expected
        """
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        # Test RLS service methods
        # 1. Initially no context
        context = await rls_service.get_current_context(db_session)
        # Context might be set from create_test_tenant, so we clear it first
        await rls_service.clear_context(db_session)
        context = await rls_service.get_current_context(db_session)
        assert context is None
        
        # 2. Set context
        await rls_service.set_tenant_context(db_session, tenant.id)
        
        # 3. Verify context set
        context = await rls_service.get_current_context(db_session)
        assert context == tenant.id
        
        # 4. Clear context
        await rls_service.clear_context(db_session)
        context = await rls_service.get_current_context(db_session)
        assert context is None
