import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from modules.b2b.models import TenantModel
from core.constants import B2BRoleName
from tests.conftest import create_test_user, create_auth_headers

class TestAccountSettings:
    
    @pytest.mark.asyncio
    async def test_get_account_settings_success(
        self,
        api_client: AsyncClient,
        b2b_test_setup: dict
    ):
        """Test retrieving account settings as an Admin"""
        setup = b2b_test_setup
        tenant = setup["tenant"]
        admin = setup["admin"]
        headers = create_auth_headers(admin, tenant)
        
        response = await api_client.get("/api/b2b/account", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == tenant.name
        assert data["domain"] == tenant.domain
        assert "logo_url" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_update_account_settings_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession,
        b2b_test_setup: dict
    ):
        """Test updating account settings"""
        setup = b2b_test_setup
        tenant = setup["tenant"]
        admin = setup["admin"]
        headers = create_auth_headers(admin, tenant)
        
        new_name = "Updated Corp"
        new_logo = "https://example.com/logo.png"
        
        response = await api_client.put(
            "/api/b2b/account",
            json={
                "name": new_name,
                "logo_url": new_logo
            },
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name
        assert data["logo_url"] == new_logo
        
        # Verify in DB
        # Re-fetch tenant to confirm persistence
        fresh_tenant = await db_session.get(TenantModel, tenant.id)
        # Note: In shared session, we might need to refresh or just check validation return
        # But 'await db_session.get' usually hits cache or DB.
        # Since response matches, we trust API, but let's check basic persistence if session allows
        assert fresh_tenant.name == new_name

    @pytest.mark.asyncio
    async def test_update_account_validation_error(
        self,
        api_client: AsyncClient,
        b2b_test_setup: dict
    ):
        """Test validation: cannot set empty name"""
        setup = b2b_test_setup
        tenant = setup["tenant"]
        admin = setup["admin"]
        headers = create_auth_headers(admin, tenant)
        
        response = await api_client.put(
            "/api/b2b/account",
            json={
                "name": "   ", # Empty/Whitespace
                "logo_url": "https://example.com/logo.png"
            },
            headers=headers
        )
        
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_account_settings_forbidden_for_member(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession,
        b2b_test_setup: dict
    ):
        """Test that a regular member cannot update account settings"""
        setup = b2b_test_setup
        tenant = setup["tenant"]
        
        # Create a member user
        member = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"member@{tenant.domain}",
            role_slug=B2BRoleName.MEMBER
        )
        member_headers = create_auth_headers(member, tenant)
        
        # Try to GET (Members might have read access depending on policy, but usually not to settings)
        # The router says: Requires account:read permission (Admin/Owner)
        # Let's check GET first
        response_get = await api_client.get("/api/b2b/account", headers=member_headers)
        assert response_get.status_code == 403
        
        # Try to PUT
        response_put = await api_client.put(
            "/api/b2b/account",
            json={"name": "Hacked Corp"},
            headers=member_headers
        )
        assert response_put.status_code == 403
