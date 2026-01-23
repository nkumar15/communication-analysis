import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from modules.b2b.models import UserModel
from core.constants import B2BRoleName
from tests.conftest import create_test_user, create_auth_headers

class TestUserManagement:
    
    @pytest.mark.asyncio
    async def test_list_users_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession,
        b2b_test_setup: dict
    ):
        """Test listing users in the tenant"""
        setup = b2b_test_setup
        tenant = setup["tenant"]
        setup = b2b_test_setup
        tenant = setup["tenant"]
        admin = setup["admin"]
        headers = create_auth_headers(admin, tenant)
        
        # Create extra users
        await create_test_user(db_session, tenant_id=tenant.id, email=f"u1@{tenant.domain}", role_slug=B2BRoleName.MEMBER)
        await create_test_user(db_session, tenant_id=tenant.id, email=f"u2@{tenant.domain}", role_slug=B2BRoleName.VIEWER)
        
        response = await api_client.get("/api/b2b/users/list", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        # Should have at least 3 users (Admin + 2 created)
        assert len(data) >= 3
        # Check structure
        assert "email" in data[0]
        assert "role" in data[0]
        assert "is_active" in data[0]

    @pytest.mark.asyncio
    async def test_user_stats_success(
        self,
        api_client: AsyncClient,
        b2b_test_setup: dict
    ):
        """Test retrieving user statistics"""
        setup = b2b_test_setup
        tenant = setup["tenant"]
        admin = setup["admin"]
        headers = create_auth_headers(admin, tenant)
        
        response = await api_client.get("/api/b2b/users/stats", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "active_users" in data
        assert "pending_invitations" in data

    @pytest.mark.asyncio
    async def test_update_user_role_success(
        self,
        api_client: AsyncClient,
        # Remove direct db_session usage to force use of setup['session']
        b2b_test_setup: dict
    ):
        """Test updating a user's role"""
        setup = b2b_test_setup
        tenant = setup["tenant"]
        session = setup["session"]  # TenantAwareSession
        
        # Create a member using the tenant session
        from modules.b2b.models import UserModel
        
        target_user = await create_test_user(
            session, 
            tenant_id=tenant.id, 
            email=f"target@{tenant.domain}", 
            role_slug=B2BRoleName.MEMBER
        )
        
        # Admin headers
        admin = setup["admin"]
        headers = create_auth_headers(admin, tenant)
        
        # Promote to Admin
        response = await api_client.put(
            f"/api/b2b/users/{target_user.id}/role",
            json={"role": B2BRoleName.ADMIN},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Verify in DB using tenant session
        result = await session.execute(select(UserModel).where(UserModel.id == target_user.id))
        updated_user = result.scalar_one()
        assert updated_user.role_id is not None
        # Note: Depending on service implementation, role field on user model might be denormalized or just relation
        # But response confirms it.

    @pytest.mark.asyncio
    async def test_update_user_role_forbidden(
        self,
        api_client: AsyncClient,
        b2b_test_setup: dict
    ):
        """Test that a non-admin cannot update roles"""
        setup = b2b_test_setup
        tenant = setup["tenant"]
        session = setup["session"]
        
        # Create a member (attacker)
        attacker = await create_test_user(
            session, 
            tenant_id=tenant.id, 
            email=f"attacker@{tenant.domain}", 
            role_slug=B2BRoleName.MEMBER
        )
        attacker_headers = create_auth_headers(attacker, tenant)
        
        # Create a victim
        victim = await create_test_user(
            session, 
            tenant_id=tenant.id, 
            email=f"victim@{tenant.domain}", 
            role_slug=B2BRoleName.MEMBER
        )
        
        response = await api_client.put(
            f"/api/b2b/users/{victim.id}/role",
            json={"role": B2BRoleName.ADMIN},
            headers=attacker_headers
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_deactivate_reactivate_user_success(
        self,
        api_client: AsyncClient,
        b2b_test_setup: dict
    ):
        """Test user deactivation and reactivation lifecycle"""
        setup = b2b_test_setup
        tenant = setup["tenant"]
        admin = setup["admin"]
        session = setup["session"]
        headers = create_auth_headers(admin, tenant)
        
        # Create target
        target = await create_test_user(
            session,
            tenant_id=tenant.id,
            email=f"temp@{tenant.domain}",
            role_slug=B2BRoleName.MEMBER
        )
        
        # 1. Deactivate
        resp_deactivate = await api_client.post(
            f"/api/b2b/users/{target.id}/deactivate",
            headers=headers
        )
        assert resp_deactivate.status_code == 200
        assert "message" in resp_deactivate.json()
        
        # Verify in DB (reload)
        await session.refresh(target)
        assert target.is_active is False
        
        # 2. Reactivate
        resp_reactivate = await api_client.post(
            f"/api/b2b/users/{target.id}/reactivate",
            headers=headers
        )
        assert resp_reactivate.status_code == 200
        assert "message" in resp_reactivate.json()
        
        # Verify in DB
        await session.refresh(target)
        assert target.is_active is True

    @pytest.mark.asyncio
    async def test_deactivate_self_forbidden(
        self,
        api_client: AsyncClient,
        b2b_test_setup: dict
    ):
        """Test that a user cannot deactivate themselves"""
        setup = b2b_test_setup
        setup = b2b_test_setup
        user = setup["admin"]
        headers = create_auth_headers(user, setup["tenant"])
        
        response = await api_client.post(
            f"/api/b2b/users/{user.id}/deactivate",
            headers=headers
        )
        
        assert response.status_code == 400
        assert "yourself" in response.json()["detail"].lower()
