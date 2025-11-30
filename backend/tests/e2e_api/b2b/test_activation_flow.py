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
class TestActivationFlow:
    """Test tenant activation workflow"""
    
    @pytest.mark.asyncio
    async def test_activation_replay_attack_prevented(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Activation token cannot be replayed after first use"""
        # Create tenant with activation token
        
        tenant = await create_test_tenant(db_session, activation_status="pending")
        
        # Set activation token manually
        from services.b2b.models import TenantModel
        from sqlalchemy import select, update
        
        activation_token = secrets.token_urlsafe(32)
        await db_session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant.id)
            .values(
                activation_token=activation_token,
                activation_expires_at=datetime.now(timezone.utc) + timedelta(days=2)
            )
        )
        
        # Create admin user and invitation
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug="admin"
        )
        
        invitation = await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=admin.email,
            role="admin"
        )
        
        await db_session.commit()
        # First activation attempt
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email
        ))

        # 1. Validate token
        response = await api_client.get(f"/api/b2b/activation/validate/{activation_token}")
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(tenant.id)
        assert data["admin_email"] == admin.email

        # 2. Get tenant info for SSO
        response = await api_client.get(f"/api/b2b/activation/tenant-info/{tenant.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["firebase_tenant_id"] == tenant.firebase_tenant_id

        # 3. Complete activation
        # Mock admin user login (handled by dependency override in conftest)
        response1 = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response1.status_code == 200
        
        # Second activation attempt (replay attack)
        response2 = await api_client.post(
            "/api/b2b/activation/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        # Should be rejected (404 Not Found because token is cleared, or 409 Conflict)
        assert response2.status_code in [404, 409]
