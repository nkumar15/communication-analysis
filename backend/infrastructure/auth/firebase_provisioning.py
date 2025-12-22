
import sys
import os
import re
from typing import Optional
import firebase_admin
from firebase_admin import auth, credentials, tenant_mgt
import requests

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from infrastructure.logging import get_logger
from infrastructure.auth.provisioning import TenantProvisioner

logger = get_logger(__name__)

from core.config import settings

class FirebaseTenantProvisioner(TenantProvisioner):
    """Firebase implementation of TenantProvisioner"""

    def sanitize_display_name(self, company_name: str) -> str:
        """
        Sanitize company name to meet Firebase display name requirements:
        - 4-20 characters
        - Start with a letter
        - Only letters, digits, and hyphens
        """
        # Remove special characters, keep only alphanumeric and hyphens
        sanitized = re.sub(r'[^a-zA-Z0-9-]', '', company_name.replace(' ', '-'))
        
        # Ensure it starts with a letter
        if not sanitized or not sanitized[0].isalpha():
            sanitized = 'T-' + sanitized  # Prefix with 'T-' for Tenant
        
        # Truncate to 20 characters max
        if len(sanitized) > 20:
            sanitized = sanitized[:20]
        
        # Ensure minimum 4 characters
        if len(sanitized) < 4:
            sanitized = sanitized + 'Org'
        
        return sanitized


    def find_firebase_tenant(self, domain: str) -> Optional[str]:
        """
        Find existing Firebase tenant by sanitized domain name
        """
        # Use domain for the unique display name
        target_name = self.sanitize_display_name(domain)
        
        try:
            # Lists tenants (returns a PageIterator)
            for tenant in tenant_mgt.list_tenants().iterate_all():
                 if tenant.display_name == target_name:
                     logger.info(f"✅ Found existing Firebase tenant: {tenant.tenant_id} ({tenant.display_name})")
                     return tenant.tenant_id
                     
        except Exception as e:
            logger.warning(f"⚠️  Error listing tenants: {e}")
            
        return None


    def create_tenant(self, company_name: str, domain: str) -> str:
        """
        Create a new Firebase tenant, OR return existing if found.
        """
        # Use sanitized domain as the consistent display name
        display_name = self.sanitize_display_name(domain)
        
        # 1. Search for existing tenant first to avoid duplicates
        existing_id = self.find_firebase_tenant(domain)
        if existing_id:
            return existing_id
        
        # 2. Create new if not found
        logger.info(f"✨ Creating New Firebase Tenant for {company_name}: {display_name}")
        try:
            tenant = tenant_mgt.create_tenant(
                display_name=display_name,
                enable_email_link_sign_in=False,  # Disable email/password - SSO only
                allow_password_sign_up=False
            )
            return tenant.tenant_id
            
        except Exception as e:
            logger.error(f"⚠️  Error creating tenant: {e}")
            raise e


    def configure_oidc_provider(
        self,
        tenant_id: str,
        provider_type: str,
        client_id: str,
        client_secret: str,
        issuer_url: str,
        provider_id_override: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> str:
        """
        Configure OIDC provider for Firebase tenant using Identity Platform API
        """
        # Get the default app to access credentials
        app = firebase_admin.get_app()
        
        # Get access token from Firebase Admin credentials
        access_token = app.credential.get_access_token().access_token
        
        # Get project ID from environment or app
        # from core.config import settings (Imported at module level)
        project_id = settings.firebase_project_id
        
        provider_id = provider_id_override or f'oidc.{provider_type}'
        
        # Base URL for OIDC configs
        base_url = f'https://identitytoolkit.googleapis.com/v2/projects/{project_id}/tenants/{tenant_id}/oauthIdpConfigs'
        
        # Identity Platform API endpoint for creating (POST)
        create_url = f'{base_url}?oauthIdpConfigId={provider_id}'
        
        # Identity Platform API endpoint for updating (PATCH)
        update_url = f'{base_url}/{provider_id}'
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Provider display name
        final_display_name = display_name or f'{provider_type.title()} SSO'
        
        # OIDC provider configuration
        data = {
            'name': f'projects/{project_id}/tenants/{tenant_id}/oauthIdpConfigs/{provider_id}',
            'displayName': final_display_name,
            'enabled': True,
            'clientId': client_id,
            'issuer': issuer_url,
            'clientSecret': client_secret,
            'responseType': {
                'code': True
            }
        }
        
        try:
            # 1. Try to CREATE (POST)
            logger.info(f"🔄 Configuring OIDC provider: {provider_id} ({final_display_name})")
            response = requests.post(create_url, headers=headers, json=data, timeout=30)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ OIDC provider created successfully")
                return provider_id
                
            elif response.status_code == 409:
                # 2. If Conflict (409), try to UPDATE (PATCH)
                logger.warning(f"⚠️  Provider exists, updating...")
                
                # For PATCH, field mask is recommended but often optional if replacing.
                # We'll try standard PATCH.
                # Note: clientSecret is sensitive, might behave differently on update?
                # Identity Platform usually allows patching it.
                
                 # Add updateMask to be safe/explicit if needed, 
                 # but usually direct PATCH works for full resource replacement logic or standard merge
                update_params = {
                    'updateMask': 'displayName,enabled,clientId,issuer,clientSecret,responseType'
                }
                
                response = requests.patch(update_url, headers=headers, json=data, params=update_params, timeout=30)
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ OIDC provider updated successfully")
                    return provider_id
                else:
                    logger.error(f"❌ Update failed: {response.status_code} - {response.text}")
                    raise Exception(f"Failed to update provider: {response.text}")
                    
            else:
                logger.error(f"⚠️  OIDC API call failed: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                logger.error(f"   Provider ID: {provider_id}")
                raise Exception(f"Failed to create provider: {response.text}")
                
        except Exception as e:
            logger.error(f"⚠️  Could not configure OIDC provider automatically: {e}")
            # Re-raise so caller knows it failed
            raise e
