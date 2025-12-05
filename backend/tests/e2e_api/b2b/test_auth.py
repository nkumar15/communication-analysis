"""
Integration tests for auth API endpoints
Tests tenant resolution and user sync functionality
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from core.constants import B2BRoleName

from tests.conftest import (
    create_test_tenant,
    create_test_user,
    create_mock_firebase_token,
    encode_mock_jwt
)


@pytest.mark.integration
class TestAuthAPI:
    """Test authentication endpoints"""
    
    @pytest.mark.asyncio
    async def test_resolve_tenant_from_email(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Resolve tenant from email address domain"""
        from uuid import uuid4
        domain = f"example-{uuid4().hex[:8]}.com"
        tenant = await create_test_tenant(db_session, domain=domain)
        
        response = await api_client.post(
            "/api/b2b/auth/resolve-tenant",
            json={"email": f"user@{domain}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Match actual TenantResolutionResponse schema
        assert data["tenant_name"] == tenant.name
        assert data["firebase_tenant_id"] == tenant.firebase_tenant_id
        assert data["domain"] == tenant.domain
        assert "tenant_id" in data


    @pytest.mark.asyncio
    async def test_resolve_tenant_not_found(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Tenant resolution fails for unknown domain"""
        response = await api_client.post(
            "/api/b2b/auth/resolve-tenant",
            json={"email": "user@unknown-domain.com"}
        )
        
        assert response.status_code == 404
        # Match actual error message format
        assert "No tenant found for domain" in response.json()["detail"]


    @pytest.mark.asyncio
    async def test_get_current_user_info(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Get current authenticated user information"""
        tenant = await create_test_tenant(db_session)
        user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"user@{tenant.domain}",
            role_slug=B2BRoleName.VIEWER
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=user.firebase_uid,
            email=user.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == user.email
        assert data["tenant_id"] == str(tenant.id)
        assert data["role"] == B2BRoleName.VIEWER


    @pytest.mark.asyncio
    async def test_sync_user_creates_missing_user(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Sync endpoint creates user if they don't exist"""
        tenant = await create_test_tenant(db_session)
        
        # Create JWT for a user that doesn't exist yet
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid="new-firebase-uid",
            email=f"newuser@{tenant.domain}",
            name="New User",
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            "/api/b2b/auth/sync-user",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Match actual response format
        assert data["message"] == "User synced successfully"
        assert data["email"] == f"newuser@{tenant.domain}"
        assert "user_id" in data
        assert "role" in data


    @pytest.mark.asyncio
    async def test_sync_user_updates_existing_user(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Sync endpoint updates existing user"""
        tenant = await create_test_tenant(db_session)
        
        # Create existing user
        user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"user@{tenant.domain}",
            role_slug=B2BRoleName.VIEWER
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=user.firebase_uid,
            email=user.email,
            name="Updated Name",
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            "/api/b2b/auth/sync-user",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "User synced successfully"
        assert data["email"] == user.email


    @pytest.mark.asyncio
    async def test_me_endpoint_without_auth(
        self,
        api_client: AsyncClient
    ):
        """GET /me requires authentication"""
        response = await api_client.get("/api/b2b/auth/me")
        
        assert response.status_code == 401


    @pytest.mark.asyncio
    async def test_sync_endpoint_without_auth(
        self,
        api_client: AsyncClient
    ):
        """POST /sync-user requires authentication"""
        response = await api_client.post("/api/b2b/auth/sync-user")
        
        assert response.status_code == 401


    @pytest.mark.asyncio
    async def test_resolve_tenant_invalid_email_format(
        self,
        api_client: AsyncClient
    ):
        """Tenant resolution validates email format"""
        response = await api_client.post(
            "/api/b2b/auth/resolve-tenant",
            json={"email": "not-an-email"}
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422
