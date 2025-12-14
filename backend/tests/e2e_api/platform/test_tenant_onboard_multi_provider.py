import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from unittest.mock import patch, MagicMock
from sqlalchemy import select, text

from services.b2b.models import TenantModel, AuthProvider
from core.constants import B2BRoleName

@pytest.mark.asyncio
class TestTenantOnboardMultiProvider:
    """Test suite for multi-provider tenant onboarding"""

    async def test_onboard_saml_provider(self, api_client: AsyncClient, platform_admin_setup, db_session: AsyncSession):
        """Test onboarding with SAML provider"""
        
        platform_admin_token = platform_admin_setup["token"]
        
        with patch('services.platform.services.tenant_onboarding_service.create_firebase_tenant') as mock_create_tenant, \
             patch('services.platform.services.tenant_onboarding_service.configure_oidc_provider') as mock_config_oidc:
            
            mock_create_tenant.return_value = f"test-tenant-{uuid4().hex[:8]}"
            # SAML doesn't call configure_oidc_provider in skeletal impl, or logic changed
            
            domain = f"saml-test-{uuid4().hex[:8]}.com"
            payload = {
                "company_name": "SAML Corp",
                "domain": domain,
                "owner_email": f"admin@{domain}",
                "provider_type": "saml",
                "provider_config": {
                    "idp_entity_id": "https://idp.example.com",
                    "sso_url": "https://idp.example.com/sso"
                }
            }
            
            response = await api_client.post(
                "/api/platform/b2b/tenants/onboard",
                json=payload,
                headers={"Authorization": f"Bearer {platform_admin_token}"}
            )
            
            if response.status_code != 201:
                print(f"❌ Error: {response.text}")
            assert response.status_code == 201
            data = response.json()
            tenant_id = data["tenant_id"]
            
            # Verify DB
            await db_session.execute(text("SET LOCAL app.is_platform_admin = 'true'"))
            auth_provider = await db_session.scalar(
                select(AuthProvider).where(AuthProvider.tenant_id == tenant_id)
            )
            
            assert auth_provider is not None
            assert auth_provider.provider_type == "saml"
            assert auth_provider.config_data["idp_entity_id"] == "https://idp.example.com"
            # In skeletal implementation, we might default provider_id to 'saml.generic' or similar if not set
            # The service sets it to f"saml.{domain_sanitized}" or "saml.generic" depending on impl
            # Let's check what it is
            print(f"SAML Provider ID: {auth_provider.provider_id}")

    async def test_onboard_google_provider(self, api_client: AsyncClient, platform_admin_setup, db_session: AsyncSession):
        """Test onboarding with Google provider (treated as OIDC)"""
        
        platform_admin_token = platform_admin_setup["token"]
        
        with patch('services.platform.services.tenant_onboarding_service.create_firebase_tenant') as mock_create_tenant, \
             patch('services.platform.services.tenant_onboarding_service.configure_oidc_provider') as mock_config_oidc:
            
            mock_create_tenant.return_value = f"test-tenant-{uuid4().hex[:8]}"
            mock_config_oidc.return_value = "oidc.google"
            
            domain = f"google-test-{uuid4().hex[:8]}.com"
            payload = {
                "company_name": "Google Corp",
                "domain": domain,
                "owner_email": f"admin@{domain}",
                "provider_type": "google",
                "provider_config": {
                    "client_id": "google-client-id",
                    "client_secret": "google-secret"
                }
            }
            
            response = await api_client.post(
                "/api/platform/b2b/tenants/onboard",
                json=payload,
                headers={"Authorization": f"Bearer {platform_admin_token}"}
            )
            
            assert response.status_code == 201
            data = response.json()
            tenant_id = data["tenant_id"]
            
            # Verify DB
            await db_session.execute(text("SET LOCAL app.is_platform_admin = 'true'"))
            auth_provider = await db_session.scalar(
                select(AuthProvider).where(AuthProvider.tenant_id == tenant_id)
            )
            
            assert auth_provider.provider_type == "google"
            assert auth_provider.config_data["client_id"] == "google-client-id"
            # Should have called configure_oidc_provider
            assert mock_config_oidc.called

    async def test_onboard_legacy_oidc_compatibility(self, api_client: AsyncClient, platform_admin_setup, db_session: AsyncSession):
        """Test onboarding with legacy top-level OIDC fields"""
        
        platform_admin_token = platform_admin_setup["token"]
        
        with patch('services.platform.services.tenant_onboarding_service.create_firebase_tenant') as mock_create_tenant, \
             patch('services.platform.services.tenant_onboarding_service.configure_oidc_provider') as mock_config_oidc:
            
            mock_create_tenant.return_value = f"test-tenant-{uuid4().hex[:8]}"
            mock_config_oidc.return_value = "oidc.generic"
            
            domain = f"legacy-oidc-{uuid4().hex[:8]}.com"
            # Payload uses old fields: oidc_client_id, etc.
            # And assumes provider_type default is 'oidc' if missing? 
            # Or if I send them, the pydantic model still supports them (as optional)
            # The service logic handles them.
            
            payload = {
                "company_name": "Legacy Corp",
                "domain": domain,
                "owner_email": f"admin@{domain}",
                "oidc_provider": "oidc",
                "oidc_client_id": "legacy-id",
                "oidc_client_secret": "legacy-secret",
                "oidc_issuer": "https://legacy.com"
            }
            
            response = await api_client.post(
                "/api/platform/b2b/tenants/onboard",
                json=payload,
                headers={"Authorization": f"Bearer {platform_admin_token}"}
            )
            
            assert response.status_code == 201
            data = response.json()
            tenant_id = data["tenant_id"]
            
            # Verify DB
            await db_session.execute(text("SET LOCAL app.is_platform_admin = 'true'"))
            auth_provider = await db_session.scalar(
                select(AuthProvider).where(AuthProvider.tenant_id == tenant_id)
            )
            
            assert auth_provider.provider_type == "oidc"
            assert auth_provider.config_data["client_id"] == "legacy-id"
