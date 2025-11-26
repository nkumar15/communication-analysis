"""
Integration tests for activation flow
Tests tenant activation scenarios
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
import secrets

from tests.conftest import (
    create_mock_firebase_token, 
    encode_mock_jwt,
    create_test_tenant,
    create_test_user,
    create_test_invitation
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
        from app.db_models import TenantModel
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
        await db_session.commit()
        
        # Create admin user and invitation
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug="admin"
        )
        
        await create_test_invitation(
            db_session,
            tenant_id=tenant.id,
            email=admin.email,
            role="admin"
        )
        
        # First activation attempt
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email
        ))
        
        response1 = await api_client.post(
            "/api/activate/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response1.status_code == 200
        
        # Second activation attempt (replay attack)
        response2 = await api_client.post(
            "/api/activate/complete",
            json={"activation_token": activation_token},
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        # Should be rejected (404 Not Found because token is cleared, or 409 Conflict)
        assert response2.status_code in [404, 409]
