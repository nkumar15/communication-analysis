from typing import Optional
from app.database import db
from app.models import Tenant


class TenantService:
    """Service for tenant operations"""
    
    async def get_tenant_by_domain(self, domain: str) -> Optional[Tenant]:
        """
        Get tenant by email domain
        
        Args:
            domain: Email domain (e.g., 'example.com')
            
        Returns:
            Tenant if found, None otherwise
        """
        query = """
            SELECT id, name, domain, firebase_tenant_id, oidc_provider_id,
                   activation_token, activation_status, activation_expires_at, activated_at, activated_by,
                   is_active, created_at, updated_at
            FROM tenants
            WHERE domain = $1 AND is_active = TRUE
        """
        
        row = await db.fetchrow(query, domain.lower())
        
        if not row:
            return None
        
        return Tenant(**dict(row))
    
    async def get_tenant_by_id(self, tenant_id: int) -> Optional[Tenant]:
        """
        Get tenant by ID
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Tenant if found, None otherwise
        """
        query = """
            SELECT id, name, domain, firebase_tenant_id, oidc_provider_id,
                   activation_token, activation_status, activation_expires_at, activated_at, activated_by,
                   is_active, created_at, updated_at
            FROM tenants
            WHERE id = $1 AND is_active = TRUE
        """
        
        row = await db.fetchrow(query, tenant_id)
        
        if not row:
            return None
        
        return Tenant(**dict(row))
    
    async def get_tenant_by_firebase_id(self, firebase_tenant_id: str) -> Optional[Tenant]:
        """
        Get tenant by Firebase tenant ID
        
        Args:
            firebase_tenant_id: Firebase tenant ID
            
        Returns:
            Tenant if found, None otherwise
        """
        query = """
            SELECT id, name, domain, firebase_tenant_id, oidc_provider_id,
                   activation_token, activation_status, activation_expires_at, activated_at, activated_by,
                   is_active, created_at, updated_at
            FROM tenants
            WHERE firebase_tenant_id = $1 AND is_active = TRUE
        """
        
        row = await db.fetchrow(query, firebase_tenant_id)
        
        if not row:
            return None
        
        return Tenant(**dict(row))
    
    def extract_domain_from_email(self, email: str) -> str:
        """
        Extract domain from email address
        
        Args:
            email: Email address
            
        Returns:
            Domain part of the email
        """
        return email.split("@")[1].lower() if "@" in email else ""


# Global tenant service instance
tenant_service = TenantService()
