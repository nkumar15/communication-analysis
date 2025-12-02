"""
Integration tests for users API endpoints
Tests user listing and statistics endpoints
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
class TestUsersAPI:
    """Test user listing and statistics endpoints"""
    
    @pytest.mark.asyncio
    async def test_admin_can_list_all_users(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Admin can list all users in their tenant"""
        tenant = await create_test_tenant(db_session)
        
        # Create admin
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        # Create other users
        viewer1 = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"viewer1@{tenant.domain}",
            role_slug=B2BRoleName.VIEWER
        )
        viewer2 = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"viewer2@{tenant.domain}",
            role_slug=B2BRoleName.VIEWER
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.get(
            "/api/b2b/users/list",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should see all 3 users
        assert len(data) == 3
        emails = [user["email"] for user in data]
        assert admin.email in emails
        assert viewer1.email in emails
        assert viewer2.email in emails
        
        # Verify structure
        for user in data:
            assert "id" in user
            assert "email" in user
            assert "role" in user
            assert "is_active" in user


    @pytest.mark.asyncio
    async def test_viewer_can_only_see_themselves(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Viewer can only see their own user record"""
        tenant = await create_test_tenant(db_session)
        
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
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
        
        response = await api_client.get(
            "/api/b2b/users/list",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Viewer should only see themselves
        assert len(data) == 1
        assert data[0]["email"] == viewer.email



    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_users_list(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Users from different tenants are isolated"""
        tenant1 = await create_test_tenant(db_session, domain="tenant1.com")
        tenant2 = await create_test_tenant(db_session, domain="tenant2.com")
        
        admin1 = await create_test_user(
            db_session,
            tenant_id=tenant1.id,
            email=f"admin@tenant1.com",
            role_slug=B2BRoleName.ADMIN
        )
        
        admin2 = await create_test_user(
            db_session,
            tenant_id=tenant2.id,
            email=f"admin@tenant2.com",
            role_slug=B2BRoleName.ADMIN
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin1.firebase_uid,
            email=admin1.email,
            firebase_tenant_id=tenant1.firebase_tenant_id
        ))
        
        response = await api_client.get(
            "/api/b2b/users/list",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only see users from tenant1
        emails = [user["email"] for user in data]
        assert admin1.email in emails
        assert admin2.email not in emails


    @pytest.mark.asyncio
    async def test_unauthenticated_access_denied(
        self,
        api_client: AsyncClient
    ):
        """Unauthenticated requests are rejected"""
        # No auth header
        response = await api_client.get("/api/b2b/users/list")
        assert response.status_code == 401
        
        response = await api_client.get("/api/b2b/users/stats")
        assert response.status_code == 401
