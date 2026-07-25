"""
E2E API Tests for B2B SSO Settings

Tests the /api/b2b/settings/sso endpoints including:
- Getting SSO configuration (OWNER/ADMIN only)
- Updating SSO credentials
- Permission enforcement
- Client ID masking
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from tests.conftest import (
    create_test_tenant,
    create_test_user,
    create_auth_headers,
    create_auth_provider
)


@pytest.mark.integration
class TestSSOSettings:
    """Test SSO settings API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_sso_config_requires_authentication(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that getting SSO config requires authentication"""
        response = await api_client.get("/api/b2b/settings/sso")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_sso_config_requires_owner_or_admin(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that only OWNER/ADMIN can view SSO config"""
        # Create tenant and member user (not owner/admin)
        tenant = await create_test_tenant(
            db_session,
            domain=f"test-sso-{uuid4().hex[:8]}.com",
            name="SSO Test Tenant"
        )
        
        member = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"member-{uuid4().hex[:8]}@test.com",
            role_slug="member"
        )
        
        headers = create_auth_headers(member, tenant)
        
        response = await api_client.get(
            "/api/b2b/settings/sso",
            headers=headers
        )
        
        assert response.status_code == 403
        assert "owners and admins" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_sso_config_success_as_owner(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test getting SSO config as tenant owner"""
        # Create tenant with SSO provider
        tenant = await create_test_tenant(
            db_session,
            domain=f"sso-owner-{uuid4().hex[:8]}.com",
            name="SSO Owner Test"
        )
        
        owner = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"owner-{uuid4().hex[:8]}@test.com",
            role_slug="owner"
        )
        
        # Create auth provider for tenant
        await create_auth_provider(db_session, tenant_id=tenant.id)
        
        headers = create_auth_headers(owner, tenant)
        
        response = await api_client.get(
            "/api/b2b/settings/sso",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "provider_type" in data
        assert "provider_id" in data
        assert "client_id" in data
        assert "client_id_masked" in data
        assert "issuer" in data
        assert "is_active" in data
        assert "has_mobile" in data
        
        # Verify client_id is masked
        assert "***" in data["client_id_masked"]
    
    @pytest.mark.asyncio
    async def test_get_sso_config_success_as_admin(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test getting SSO config as tenant admin"""
        tenant = await create_test_tenant(
            db_session,
            domain=f"sso-admin-{uuid4().hex[:8]}.com",
            name="SSO Admin Test"
        )
        
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin-{uuid4().hex[:8]}@test.com",
            role_slug="admin"
        )
        
        # Create auth provider for tenant
        await create_auth_provider(db_session, tenant_id=tenant.id)
        
        headers = create_auth_headers(admin, tenant)
        
        response = await api_client.get(
            "/api/b2b/settings/sso",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "client_id_masked" in data
    
    @pytest.mark.asyncio
    async def test_get_sso_config_with_mobile_credentials(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test SSO config includes mobile credentials if configured"""
        tenant = await create_test_tenant(
            db_session,
            domain=f"sso-mobile-{uuid4().hex[:8]}.com",
            name="SSO Mobile Test"
        )
        
        owner = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"owner-{uuid4().hex[:8]}@test.com",
            role_slug="owner"
        )
        
        # Create auth provider for tenant
        await create_auth_provider(db_session, tenant_id=tenant.id)
        
        headers = create_auth_headers(owner, tenant)
        
        response = await api_client.get(
            "/api/b2b/settings/sso",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check mobile credentials fields exist
        assert "has_mobile" in data
        assert "mobile_client_id" in data
        assert "mobile_client_id_masked" in data
    
    @pytest.mark.asyncio
    async def test_update_sso_config_requires_authentication(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that updating SSO config requires authentication"""
        response = await api_client.put(
            "/api/b2b/settings/sso",
            json={
                "client_id": "new-client-id",
                "client_secret": "new-secret",
                "issuer": "https://issuer.com"
            }
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_update_sso_config_requires_owner_or_admin(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that only OWNER/ADMIN can update SSO config"""
        tenant = await create_test_tenant(
            db_session,
            domain=f"update-sso-{uuid4().hex[:8]}.com",
            name="Update SSO Test"
        )
        
        member = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"member-{uuid4().hex[:8]}@test.com",
            role_slug="member"
        )
        
        headers = create_auth_headers(member, tenant)
        
        response = await api_client.put(
            "/api/b2b/settings/sso",
            headers=headers,
            json={
                "client_id": "new-client-id",
                "client_secret": "new-secret",
                "issuer": "https://issuer.com"
            }
        )
        
        assert response.status_code == 403
        assert "owners and admins" in response.json()["detail"].lower()
    
    @pytest.mark.skip(reason="Requires Firebase Admin SDK initialization")

    
    @pytest.mark.asyncio
    async def test_update_sso_config_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test successfully updating SSO configuration"""
        tenant = await create_test_tenant(
            db_session,
            domain=f"update-success-{uuid4().hex[:8]}.com",
            name="Update Success Test"
        )
        
        owner = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"owner-{uuid4().hex[:8]}@test.com",
            role_slug="owner"
        )
        
        # Create auth provider for tenant
        await create_auth_provider(db_session, tenant_id=tenant.id)
        
        headers = create_auth_headers(owner, tenant)
        
        new_config = {
            "client_id": f"client-{uuid4().hex[:12]}",
            "client_secret": f"secret-{uuid4().hex}",
            "issuer": "https://auth.example.com"
        }
        
        response = await api_client.put(
            "/api/b2b/settings/sso",
            headers=headers,
            json=new_config
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        
        # Verify config was actually updated by fetching it
        get_response = await api_client.get(
            "/api/b2b/settings/sso",
            headers=headers
        )
        
        assert get_response.status_code == 200
        updated_data = get_response.json()
        assert updated_data["client_id"] == new_config["client_id"]
        assert updated_data["issuer"] == new_config["issuer"]
    
    @pytest.mark.skip(reason="Requires Firebase Admin SDK initialization")

    
    @pytest.mark.asyncio
    async def test_update_sso_config_with_mobile_credentials(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test updating SSO config with mobile credentials"""
        tenant = await create_test_tenant(
            db_session,
            domain=f"mobile-update-{uuid4().hex[:8]}.com",
            name="Mobile Update Test"
        )
        
        owner = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"owner-{uuid4().hex[:8]}@test.com",
            role_slug="owner"
        )
        
        # Create auth provider for tenant
        await create_auth_provider(db_session, tenant_id=tenant.id)
        
        headers = create_auth_headers(owner, tenant)
        
        new_config = {
            "client_id": f"web-client-{uuid4().hex[:12]}",
            "client_secret": f"web-secret-{uuid4().hex}",
            "issuer": "https://auth.example.com",
            "mobile_client_id": f"mobile-client-{uuid4().hex[:12]}",
            "mobile_client_secret": f"mobile-secret-{uuid4().hex}"
        }
        
        response = await api_client.put(
            "/api/b2b/settings/sso",
            headers=headers,
            json=new_config
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify mobile credentials were saved
        get_response = await api_client.get(
            "/api/b2b/settings/sso",
            headers=headers
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["has_mobile"] is True
        assert data["mobile_client_id"] == new_config["mobile_client_id"]
        assert "***" in data["mobile_client_id_masked"]
    
    @pytest.mark.asyncio
    async def test_update_sso_config_validation(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test input validation for SSO config updates"""
        tenant = await create_test_tenant(
            db_session,
            domain=f"validation-{uuid4().hex[:8]}.com",
            name="Validation Test"
        )
        
        owner = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"owner-{uuid4().hex[:8]}@test.com",
            role_slug="owner"
        )
        
        # Create auth provider for tenant
        await create_auth_provider(db_session, tenant_id=tenant.id)
        
        headers = create_auth_headers(owner, tenant)
        
        # Test missing required fields
        invalid_configs = [
            {},  # Empty
            {"client_id": "test"},  # Missing client_secret and issuer
            {"client_secret": "secret"},  # Missing client_id and issuer
            {"client_id": "", "client_secret": "secret", "issuer": "https://test.com"},  # Empty client_id
        ]
        
        for invalid_config in invalid_configs:
            response = await api_client.put(
                "/api/b2b/settings/sso",
                headers=headers,
                json=invalid_config
            )
            assert response.status_code == 422, f"Expected 422 for invalid config: {invalid_config}"
