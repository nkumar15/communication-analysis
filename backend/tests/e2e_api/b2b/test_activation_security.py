"""
Integration tests for activation flow
Tests tenant activation scenarios
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from services.b2b.models import TenantModel, UserModel
from core.config import settings
from datetime import datetime, timedelta, timezone
import secrets

from tests.conftest import (
    create_test_user,
    create_test_invitation,
    create_mock_firebase_token,
    encode_mock_jwt,
    create_test_tenant
)


@pytest.mark.integration
class TestActivationSecurity:
    """Test tenant activation security scenarios"""

    
    @pytest.mark.asyncio
    async def test_activation_replay_attack_prevented(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        Test activation replay attack prevention
        
        ACTIVATION FLOW OVERVIEW:
        1. Platform admin creates tenant via platform portal
        2. System generates a single token used for BOTH:
           - tenant.activation_token (identifies pending tenant)
           - invitation.invitation_token (invites the owner)
        3. Token is sent in activation email to tenant owner
        4. Owner clicks link -> validates token -> performs SSO login -> completes activation
        5. After successful activation, token should be invalidated to prevent replay
        
        This test verifies step 5: the token cannot be reused after first activation.
        """
        from services.b2b.models import TenantModel
        from sqlalchemy import select, update
        from core.constants import B2BRoleName
        
        # Create tenant in pending state (simulating platform admin creating it)
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        # Generate a single activation token (used by both tenant and invitation)
        activation_token = secrets.token_urlsafe(32)
        
        # Set activation token on tenant
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(
                activation_token=activation_token,
                activation_expires_at=datetime.now(timezone.utc) + timedelta(days=2)
            )
        )
        
        # Create owner user (will be activated during onboarding)
        owner = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"owner@{tenant.domain}",
            role_slug=B2BRoleName.OWNER  # OWNER role for tenant activation
        )
        
        # Create invitation with THE SAME TOKEN as tenant activation_token
        # In real flow: platform creates both tenant + invitation with same token
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=owner.email,
            role=B2BRoleName.OWNER
        )
        
        # CRITICAL: Set invitation token to match activation token
        invitation.invitation_token = activation_token
        
        await db_session.commit()
        
        # Simulate owner's SSO login (JWT token from Firebase)
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=owner.firebase_uid,
            email=owner.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))

        # Step 1: Validate activation token (when owner clicks email link)
        response = await api_client.get(f"/api/b2b/activation/validate/{activation_token}")
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(tenant.id)
        assert data["admin_email"] == owner.email

        # Step 2: Get tenant SSO config (for frontend to initiate OIDC flow)
        response = await api_client.get(f"/api/b2b/activation/tenant-info/{tenant.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["firebase_tenant_id"] == tenant.firebase_tenant_id

        # Step 3: Complete activation (after successful SSO login)
        response1 = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response1.status_code == 200
        
        # REPLAY ATTACK ATTEMPT: Try to activate again with same token
        response2 = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        # Should be rejected (404 if token cleared, 409 if grace period expired)
        assert response2.status_code in [404, 409]
