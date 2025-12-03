import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from services.b2b.models import TenantModel, AuthProvider
from services.b2b.services.invitation_service import invitation_service
from core.constants import B2BRoleName
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
class TestTenantOnboarding:
    """Test suite for platform tenant onboarding"""

    async def test_onboard_tenant_success(self, api_client: AsyncClient, platform_admin_setup, db_session: AsyncSession):
        """Test full tenant onboarding workflow"""
        
        platform_admin_token = platform_admin_setup["token"]
        
        # Mock Firebase interactions
        with patch('services.platform.services.tenant_onboarding_service.create_firebase_tenant') as mock_create_tenant, \
             patch('services.platform.services.tenant_onboarding_service.configure_oidc_provider') as mock_config_oidc:
            
            mock_create_tenant.return_value = f"test-tenant-{uuid4().hex[:8]}"
            mock_config_oidc.return_value = "oidc.auth0"
            
                # Unique data for this test
            domain = f"test-onboard-{uuid4().hex[:8]}.com"
            company = f"Test Corp {uuid4().hex[:4]}"
            email = f"admin@{domain}"
            
            payload = {
                "company_name": company,
                "domain": domain,
                "owner_email": email,
                "oidc_provider": "auth0",
                "oidc_client_id": "test-client-id",
                "oidc_client_secret": "test-client-secret",
                "oidc_issuer": "https://test.auth0.com/"
            }
            
            # 1. Call Onboard Endpoint
            response = await api_client.post(
                "/api/platform/tenants/onboard",
                json=payload,
                headers={"Authorization": f"Bearer {platform_admin_token}"}
            )
            
            if response.status_code != 201:
                print(f"\n❌ Error Response: {response.text}")
                
            assert response.status_code == 201
            data = response.json()
            
            # Verify response structure
            assert data["tenant_name"] == company
            assert data["domain"] == domain
            assert "activation_url" in data
            assert "activation_token" in data
            
            tenant_id = data["tenant_id"]
            
            # 2. Verify Database State
            
            # Check Tenant
            tenant = await db_session.get(TenantModel, tenant_id)
            assert tenant is not None
            assert tenant.name == company
            assert tenant.domain == domain
            assert tenant.activation_status == "pending"
            assert tenant.is_active == True
            
            # Check Auth Provider
            from sqlalchemy import select
            auth_provider = await db_session.scalar(
                select(AuthProvider).where(AuthProvider.tenant_id == tenant_id)
            )
            assert auth_provider is not None
            assert auth_provider.provider_type == "oidc"
            assert auth_provider.is_primary == True
            
            # Check Default Team
            from services.b2b.models import Team
            default_team = await db_session.scalar(
                select(Team).where(Team.tenant_id == tenant_id).where(Team.is_default == True)
            )
            assert default_team is not None
            
            # Check Admin Invitation
            from services.b2b.models import InvitationModel
            invitation = await db_session.scalar(
                select(InvitationModel)
                .where(InvitationModel.tenant_id == tenant_id)
                .where(InvitationModel.email == email)
            )
            assert invitation is not None
            assert invitation.role == B2BRoleName.OWNER
        
    async def test_get_tenant_details(self, api_client: AsyncClient, platform_admin_setup, db_session: AsyncSession):
        """Test fetching tenant details"""
        
        platform_admin_token = platform_admin_setup["token"]
        
        # Mock Firebase interactions
        with patch('services.platform.services.tenant_onboarding_service.create_firebase_tenant') as mock_create_tenant, \
             patch('services.platform.services.tenant_onboarding_service.configure_oidc_provider') as mock_config_oidc:
            
            mock_create_tenant.return_value = f"test-tenant-{uuid4().hex[:8]}"
            mock_config_oidc.return_value = "oidc.auth0"

            # Create a test tenant first (using the onboarding endpoint for convenience)
            domain = f"test-details-{uuid4().hex[:8]}.com"
            payload = {
                "company_name": "Details Corp",
                "domain": domain,
                "owner_email": f"admin@{domain}",
                "oidc_provider": "auth0",
                "oidc_client_id": "id",
                "oidc_client_secret": "secret",
                "oidc_issuer": "https://issuer.com"
            }
            
            create_res = await api_client.post(
                "/api/platform/tenants/onboard",
                json=payload,
                headers={"Authorization": f"Bearer {platform_admin_token}"}
            )
            tenant_id = create_res.json()["tenant_id"]
            
            # Get Details
            response = await api_client.get(
                f"/api/platform/tenants/{tenant_id}/details",
                headers={"Authorization": f"Bearer {platform_admin_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["id"] == tenant_id
            assert data["name"] == "Details Corp"
            assert data["auth_provider"]["provider_type"] == "oidc"
            assert data["team_count"] >= 1  # Default team
        
    async def test_resend_activation(self, api_client: AsyncClient, platform_admin_setup, db_session: AsyncSession):
        """Test resending activation email"""
        
        platform_admin_token = platform_admin_setup["token"]
        
        # Mock Firebase interactions
        with patch('services.platform.services.tenant_onboarding_service.create_firebase_tenant') as mock_create_tenant, \
             patch('services.platform.services.tenant_onboarding_service.configure_oidc_provider') as mock_config_oidc:
            
            mock_create_tenant.return_value = f"test-tenant-{uuid4().hex[:8]}"
            mock_config_oidc.return_value = "oidc.auth0"

            # Create tenant
            domain = f"test-resend-{uuid4().hex[:8]}.com"
            payload = {
                "company_name": "Resend Corp",
                "domain": domain,
                "owner_email": f"admin@{domain}",
                "oidc_provider": "auth0",
                "oidc_client_id": "id",
                "oidc_client_secret": "secret",
                "oidc_issuer": "https://issuer.com"
            }
            
            create_res = await api_client.post(
                "/api/platform/tenants/onboard",
                json=payload,
                headers={"Authorization": f"Bearer {platform_admin_token}"}
            )
            tenant_id = create_res.json()["tenant_id"]
            original_token = create_res.json()["activation_token"]
            
            # Resend Activation
            response = await api_client.post(
                f"/api/platform/tenants/{tenant_id}/resend-activation",
                headers={"Authorization": f"Bearer {platform_admin_token}"}
            )
            
            if response.status_code != 200:
                print(f"\n❌ Resend Error: {response.text}")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify token changed in DB
            tenant = await db_session.get(TenantModel, tenant_id)
            assert tenant.activation_token != original_token
        
    async def test_deactivate_tenant(self, api_client: AsyncClient, platform_admin_setup, db_session: AsyncSession):
        """Test deactivating a tenant"""
        
        platform_admin_token = platform_admin_setup["token"]
        
        # Mock Firebase interactions
        with patch('services.platform.services.tenant_onboarding_service.create_firebase_tenant') as mock_create_tenant, \
             patch('services.platform.services.tenant_onboarding_service.configure_oidc_provider') as mock_config_oidc:
            
            mock_create_tenant.return_value = f"test-tenant-{uuid4().hex[:8]}"
            mock_config_oidc.return_value = "oidc.auth0"

            # Create tenant
            domain = f"test-deactivate-{uuid4().hex[:8]}.com"
            payload = {
                "company_name": "Deactivate Corp",
                "domain": domain,
                "owner_email": f"admin@{domain}",
                "oidc_provider": "auth0",
                "oidc_client_id": "id",
                "oidc_client_secret": "secret",
                "oidc_issuer": "https://issuer.com"
            }
            
            create_res = await api_client.post(
                "/api/platform/tenants/onboard",
                json=payload,
                headers={"Authorization": f"Bearer {platform_admin_token}"}
            )
            tenant_id = create_res.json()["tenant_id"]
            
            # Deactivate
            response = await api_client.patch(
                f"/api/platform/tenants/{tenant_id}/deactivate",
                headers={"Authorization": f"Bearer {platform_admin_token}"}
            )
            
            assert response.status_code == 200
            
            # Verify in DB
            tenant = await db_session.get(TenantModel, tenant_id)
            assert tenant.is_active == False
