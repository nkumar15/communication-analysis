"""
Security tests for platform admin endpoints
Tests access control and isolation
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from core.constants import RoleName
from services.platform.models import PlatformUser, PlatformRole
from core.config import settings

from tests.conftest import (
    create_mock_firebase_token, 
    encode_mock_jwt,
    create_test_user,
    create_test_tenant
)


@pytest.mark.security
class TestPlatformSecurity:
    """Test platform security and access controls"""
    
    @pytest.mark.asyncio
    async def test_regular_user_cannot_access_platform_api(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Regular tenant user cannot access platform endpoints"""
        # Setup regular tenant
        tenant = await create_test_tenant(db_session)
        user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"user@{tenant.domain}",
            role_slug="field_agent"
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=user.firebase_uid,
            email=user.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Try to access platform stats
        response = await api_client.get(
            "/api/platform/stats",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_tenant_admin_cannot_access_platform_api(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Tenant admin cannot access platform endpoints"""
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug="admin"
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Try to list tenants
        response = await api_client.get(
            "/api/platform/tenants",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_access_denied(
        self,
        api_client: AsyncClient
    ):
        """Unauthenticated request is denied"""
        response = await api_client.get("/api/platform/stats")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
