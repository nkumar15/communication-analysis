"""
Negative test cases for tenant activation errors

Tests error scenarios and edge cases in the activation flow
to ensure proper error handling and security.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from uuid import uuid4
from datetime import datetime, timezone, timedelta
import secrets

from services.b2b.models import TenantModel
from services.b2b.services.rls_service import rls_service
from core.constants import B2BRoleName
from tests.conftest import (
    create_test_tenant,
    create_test_user,
    create_test_invitation,
    create_mock_firebase_token,
    encode_mock_jwt
)


@pytest.mark.integration
class TestActivationErrors:
    """Test error cases in activation flow"""
    
    @pytest.mark.asyncio
    async def test_activation_with_invalid_token(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that activation fails with nonexistent/invalid token"""
        fake_token = secrets.token_urlsafe(32)
        
        # Try to validate invalid token
        response = await api_client.get(f"/api/b2b/activation/validate/{fake_token}")
        
        assert response.status_code == 404
        assert "invalid" in response.json()["detail"].lower()
    
    
    @pytest.mark.asyncio
    async def test_activation_with_wrong_email(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that activation fails when user email doesn't match invitation"""
        # Create pending tenant with activation
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        activation_token = secrets.token_urlsafe(32)
        correct_email = f"owner@{tenant.domain}"
        wrong_email = f"hacker@{tenant.domain}"
        
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(
                activation_token=activation_token,
                activation_expires_at=datetime.now(timezone.utc) + timedelta(days=2)
            )
        )
        
        await rls_service.set_tenant_context(db_session, tenant.id)
        
        # Create invitation for correct email
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=correct_email,
            role=B2BRoleName.OWNER
        )
        invitation.invitation_token = activation_token
        
        # Create user with WRONG email
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        wrong_user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=wrong_email,  # Wrong email!
            firebase_uid=firebase_uid,
            role_slug=B2BRoleName.OWNER
        )
        await db_session.commit()
        
        # Try to complete activation with wrong user
        wrong_jwt = encode_mock_jwt(create_mock_firebase_token(
            uid=firebase_uid,
            email=wrong_email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        complete_response = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {wrong_jwt}"}
        )
        
        # Should fail - user exists but email doesn't match invitation
        assert complete_response.status_code in [403, 404]
    
    
    @pytest.mark.asyncio
    async def test_activation_with_non_owner_role(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that non-owner user cannot activate tenant"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        activation_token = secrets.token_urlsafe(32)
        viewer_email = f"viewer@{tenant.domain}"
        
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(
                activation_token=activation_token,
                activation_expires_at=datetime.now(timezone.utc) + timedelta(days=2)
            )
        )
        
        await rls_service.set_tenant_context(db_session, tenant.id)
        
        # Create invitation and user with VIEWER role
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=viewer_email,
            role=B2BRoleName.VIEWER  # Not owner!
        )
        invitation.invitation_token = activation_token
        
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        viewer_user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=viewer_email,
            firebase_uid=firebase_uid,
            role_slug=B2BRoleName.VIEWER  # Viewer cannot activate!
        )
        await db_session.commit()
        
        # Try to complete activation as viewer
        viewer_jwt = encode_mock_jwt(create_mock_firebase_token(
            uid=firebase_uid,
            email=viewer_email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        complete_response = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {viewer_jwt}"}
        )
        
        assert complete_response.status_code == 403
        assert "owner" in complete_response.json()["detail"].lower()
    
    
    @pytest.mark.asyncio
    async def test_activation_with_expired_token(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that activation fails with expired token"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        activation_token = secrets.token_urlsafe(32)
        
        # Set expiry to PAST
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(
                activation_token=activation_token,
                activation_expires_at=datetime.now(timezone.utc) - timedelta(days=1)  # Expired!
            )
        )
        await db_session.commit()
        
        # Try to validate expired token
        validate_response = await api_client.get(
            f"/api/b2b/activation/validate/{activation_token}"
        )
        
        assert validate_response.status_code == 410  # Gone
        assert "expired" in validate_response.json()["detail"].lower()
    
    
    @pytest.mark.asyncio
    async def test_pending_tenant_users_cannot_access_b2b_endpoints(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test that users belonging to pending tenant cannot access B2B endpoints
        
        This ensures that even if a user is created during activation,
        they can't use the system until activation is complete.
        """
        # Create pending tenant
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        await rls_service.set_tenant_context(db_session, tenant.id)
        
        # Create user in pending tenant
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"user@{tenant.domain}",
            firebase_uid=firebase_uid,
            role_slug=B2BRoleName.OWNER
        )
        await db_session.commit()
        
        # Create JWT for this user
        user_jwt = encode_mock_jwt(create_mock_firebase_token(
            uid=firebase_uid,
            email=user.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Try to access B2B endpoints with pending tenant
        # NOTE: Standard B2B middleware should reject this
        
        # Try to list invitations
        list_response = await api_client.get(
            "/api/b2b/invitations/list",
            headers={"Authorization": f"Bearer {user_jwt}"}
        )
        
        # Should fail - tenant is not active
        # Depending on middleware implementation, could be 403 or 401
        assert list_response.status_code in [401, 403]
    
    
    @pytest.mark.asyncio
    async def test_double_activation_prevented(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that tenant cannot be activated twice"""
        # Create tenant that's already active
        tenant = await create_test_tenant(db_session, activation_status="active")
        
        activation_token = secrets.token_urlsafe(32)
        owner_email = f"owner@{tenant.domain}"
        
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(activation_token=activation_token)
        )
        
        await rls_service.set_tenant_context(db_session, tenant.id)
        
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        owner = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=owner_email,
            firebase_uid=firebase_uid,
            role_slug=B2BRoleName.OWNER
        )
        await db_session.commit()
        
        # Try to validate token for already-active tenant
        validate_response = await api_client.get(
            f"/api/b2b/activation/validate/{activation_token}"
        )
        
        assert validate_response.status_code == 400
        assert "already activated" in validate_response.json()["detail"].lower()
    
    
    @pytest.mark.asyncio
    async def test_activation_without_invitation(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test activation fails if no invitation exists for the token"""
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        activation_token = secrets.token_urlsafe(32)
        
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(
                activation_token=activation_token,
                activation_expires_at=datetime.now(timezone.utc) + timedelta(days=2)
            )
        )
        await db_session.commit()
        
        # Do NOT create invitation - this simulates data inconsistency
        
        # Try to validate - should fail because no invitation exists
        validate_response = await api_client.get(
            f"/api/b2b/activation/validate/{activation_token}"
        )
        
        assert validate_response.status_code == 404
        assert "invitation not found" in validate_response.json()["detail"].lower()
    
    
    @pytest.mark.asyncio
    async def test_concurrent_activation_prevented(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test that concurrent activation attempts are prevented
        
        This is the replay attack prevention test, ensuring
        activation_started_at prevents race conditions.
        """
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        activation_token = secrets.token_urlsafe(32)
        owner_email = f"owner@{tenant.domain}"
        
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(
                activation_token=activation_token,
                activation_expires_at=datetime.now(timezone.utc) + timedelta(days=2),
                activation_started_at=datetime.now(timezone.utc) - timedelta(hours=1)  # Already started!
            )
        )
        
        await rls_service.set_tenant_context(db_session, tenant.id)
        
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=owner_email,
            role=B2BRoleName.OWNER
        )
        invitation.invitation_token = activation_token
        
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        owner = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=owner_email,
            firebase_uid=firebase_uid,
            role_slug=B2BRoleName.OWNER
        )
        await db_session.commit()
        
        owner_jwt = encode_mock_jwt(create_mock_firebase_token(
            uid=firebase_uid,
            email=owner_email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Try to complete activation - should fail due to replay protection
        complete_response = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {owner_jwt}"}
        )
        
        # Should fail - activation already started more than grace period ago
        assert complete_response.status_code == 409  # Conflict
        assert "already in progress" in complete_response.json()["detail"].lower()
