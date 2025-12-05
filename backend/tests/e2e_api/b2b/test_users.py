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
    async def test_admin_can_list_all_users(self, api_client: AsyncClient, b2b_test_setup):
        """Test that admin can list all users in their tenant"""
        setup = b2b_test_setup
        
        # Create additional users
        await create_test_user(
            setup['session'],
            tenant_id=setup["tenant_id"],
            email=f"user1@{setup['tenant'].domain}",
            role_slug="viewer"
        )
        await create_test_user(
            setup['session'],
            tenant_id=setup["tenant_id"],
            email=f"user2@{setup['tenant'].domain}",
            role_slug="viewer"
        )
        
        response = await api_client.get(
            "/api/b2b/users/list",
            headers={"Authorization": f"Bearer {setup['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # Admin + 2 viewers
        
        # Verify structure
        for user in data:
            assert "id" in user
            assert "email" in user
            assert "role" in user
            assert "is_active" in user



    @pytest.mark.asyncio
    async def test_viewer_can_only_see_themselves(self, api_client: AsyncClient, b2b_test_setup):
        """Test that viewer role can only see their own user"""
        setup = b2b_test_setup
        
        # Create a viewer user
        viewer = await create_test_user(
            setup['session'],
            tenant_id=setup["tenant_id"],
            email=f"viewer@{setup['tenant'].domain}",
            role_slug="viewer"
        )
        viewer_token = encode_mock_jwt(create_mock_firebase_token(
            uid=viewer.firebase_uid,
            email=viewer.email,
            firebase_tenant_id=setup['tenant'].firebase_tenant_id
        ))
        
        response = await api_client.get(
            "/api/b2b/users/list",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == viewer.email



    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_users_list(self, api_client: AsyncClient, b2b_test_setup):
        """Test that users from one tenant cannot see users from another tenant"""
        # Setup for tenant 1
        setup1 = b2b_test_setup
        
        # Create second tenant (need raw db_session for this)
        
        # Get underlying session
        underlying_session = setup1['session']._session
        tenant2 = await create_test_tenant(underlying_session, name="Tenant 2", domain="tenant2.com")
        admin2 = await create_test_user(
            underlying_session,
            tenant_id=tenant2.id,
            email=f"admin@{tenant2.domain}",
            role_slug="admin"
        )
        admin2_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin2.firebase_uid,
            email=admin2.email,
            firebase_tenant_id=tenant2.firebase_tenant_id
        ))
        
        # Tenant1 admin requests users
        response1 = await api_client.get(
            "/api/b2b/users/list",
            headers={"Authorization": f"Bearer {setup1['token']}"}
        )
        
        # Tenant2 admin requests users
        response2 = await api_client.get(
            "/api/b2b/users/list",
            headers={"Authorization": f"Bearer {admin2_token}"}
        )
        
        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # But see different users
        users1 = {u["email"] for u in response1.json()}
        users2 = {u["email"] for u in response2.json()}
        
        # No overlap
        assert len(users1.intersection(users2)) == 0
        assert setup1['admin'].email in users1
        assert admin2.email in users2


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
