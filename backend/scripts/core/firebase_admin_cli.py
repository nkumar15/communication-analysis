"""
Firebase tenant management functions for CLI
"""
import argparse
import sys
import os
import json
import firebase_admin
from firebase_admin import auth, credentials, tenant_mgt
import requests

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config import settings


def sanitize_display_name(company_name: str) -> str:
    """
    Sanitize company name to meet Firebase display name requirements:
    - 4-20 characters
    - Start with a letter
    - Only letters, digits, and hyphens
    """
    import re
    
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


def create_firebase_tenant(company_name: str) -> str:
    """
    Create a new Firebase tenant
    
    Args:
        company_name: Display name for the tenant
        
    Returns:
        Firebase tenant ID
    """
    display_name = sanitize_display_name(company_name)
    
    tenant = tenant_mgt.create_tenant(
        display_name=display_name,
        enable_email_link_sign_in=False,  # Disable email/password - SSO only
        allow_password_sign_up=False
    )
    return tenant.tenant_id


def configure_oidc_provider(
    firebase_tenant_id: str,
    provider_type: str,
    client_id: str,
    client_secret: str,
    issuer_url: str,
    provider_id_override: str = None
) -> str:
    """
    Configure OIDC provider for Firebase tenant using Identity Platform API
    
    Args:
        firebase_tenant_id: Firebase tenant ID
        provider_type: Provider type (auth0, okta, google, azure)
        client_id: OIDC client ID
        client_secret: OIDC client secret
        issuer_url: OIDC issuer URL
        provider_id_override: Optional explicitly defined provider ID string
        
    Returns:
        Provider ID (e.g., 'oidc.auth0')
    """
    # Get the default app to access credentials
    app = firebase_admin.get_app()
    
    # Get access token from Firebase Admin credentials
    access_token = app.credential.get_access_token().access_token
    
    # Get project ID from environment or app
    from core.config import settings
    project_id = settings.firebase_project_id
    
    provider_id = provider_id_override or f'oidc.{provider_type}'
    
    # Identity Platform API endpoint
    url = f'https://identitytoolkit.googleapis.com/v2/projects/{project_id}/tenants/{firebase_tenant_id}/inboundSamlConfigs?inboundSamlConfigId={provider_id}'
    
    # For OIDC, we need to use defaultSupportedIdpConfigs endpoint instead
    oidc_url = f'https://identitytoolkit.googleapis.com/v2/projects/{project_id}/tenants/{firebase_tenant_id}/oauthIdpConfigs?oauthIdpConfigId={provider_id}'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # OIDC provider configuration
    data = {
        'name': f'projects/{project_id}/tenants/{firebase_tenant_id}/oauthIdpConfigs/{provider_id}',
        'displayName': f'{provider_type.title()} SSO',
        'enabled': True,
        'clientId': client_id,
        'issuer': issuer_url,
        'clientSecret': client_secret,
        'responseType': {
            'code': True
        }
    }
    
    try:
        response = requests.post(oidc_url, headers=headers, json=data)
        
        if response.status_code in [200, 201]:
            print(f"✅ OIDC provider configured successfully via API")
            return provider_id
        else:
            print(f"⚠️  OIDC API call failed: {response.status_code}")
            print(f"   Response: {response.text}")
            print(f"   Provider ID: {provider_id}")
            print(f"   Please configure manually in Firebase Console:")
            print(f"   https://console.firebase.google.com/project/{project_id}/authentication/providers")
            return provider_id
            
    except Exception as e:
        print(f"⚠️  Could not configure OIDC provider automatically: {e}")
        print(f"   Provider ID: {provider_id}")
        print(f"   Client ID: {client_id}")
        print(f"   Issuer: {issuer_url}")
        print(f"   Please configure manually in Firebase Console:")
        print(f"   https://console.firebase.google.com/project/{project_id}/authentication/providers")
        return provider_id
