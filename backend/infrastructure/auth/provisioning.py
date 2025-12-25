
from abc import ABC, abstractmethod
from typing import Optional

class TenantProvisioner(ABC):
    """Abstract base class for tenant provisioning providers"""
    
    @abstractmethod
    def create_tenant(self, company_name: str, domain: str) -> str:
        """
        Create a new tenant in the identity provider.
        
        Args:
            company_name: Display name for the tenant
            domain: Domain name (used for uniqueness)
            
        Returns:
            Tenant ID
        """
        pass

    @abstractmethod
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
        Configure OIDC provider for a tenant.
        
        Returns:
            Provider ID
        """
        pass


