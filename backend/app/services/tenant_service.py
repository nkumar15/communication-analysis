from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db_models import TenantModel
from app.models import Tenant


class TenantService:
    """Service for tenant operations using SQLAlchemy ORM"""
    
    async def get_tenant_by_domain(self, db: AsyncSession, domain: str) -> Optional[Tenant]:
        """
        Get tenant by email domain
        
        Args:
            db: Database session
            domain: Email domain (e.g., 'example.com')
            
        Returns:
            Tenant if found, None otherwise
        """
        result = await db.execute(
            select(TenantModel)
            .where(TenantModel.domain == domain.lower())
            .where(TenantModel.is_active == True)
        )
        tenant_model = result.scalar_one_or_none()
        
        if not tenant_model:
            return None
        
        return self._model_to_pydantic(tenant_model)
    
    async def get_tenant_by_id(self, db: AsyncSession, tenant_id: UUID) -> Optional[Tenant]:
        """
        Get tenant by ID
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            
        Returns:
            Tenant if found, None otherwise
        """
        result = await db.execute(
            select(TenantModel)
            .where(TenantModel.id == tenant_id)
            .where(TenantModel.is_active == True)
        )
        tenant_model = result.scalar_one_or_none()
        
        if not tenant_model:
            return None
        
        return self._model_to_pydantic(tenant_model)
    
    async def get_tenant_by_firebase_id(self, db: AsyncSession, firebase_tenant_id: str) -> Optional[Tenant]:
        """
        Get tenant by Firebase tenant ID
        
        Args:
            db: Database session
            firebase_tenant_id: Firebase tenant ID
            
        Returns:
            Tenant if found, None otherwise
        """
        result = await db.execute(
            select(TenantModel)
            .where(TenantModel.firebase_tenant_id == firebase_tenant_id)
            .where(TenantModel.is_active == True)
        )
        tenant_model = result.scalar_one_or_none()
        
        if not tenant_model:
            return None
        
        return self._model_to_pydantic(tenant_model)
    
    async def get_tenant_by_activation_token(self, db: AsyncSession, token: str) -> Optional[Tenant]:
        """
        Get tenant by activation token
        
        Args:
            db: Database session
            token: Activation token
            
        Returns:
            Tenant if found, None otherwise
        """
        result = await db.execute(
            select(TenantModel)
            .where(TenantModel.activation_token == token)
        )
        tenant_model = result.scalar_one_or_none()
        
        if not tenant_model:
            return None
        
        return self._model_to_pydantic(tenant_model)
    
    async def activate_tenant(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        activated_by_user_id: UUID
    ) -> Tenant:
        """
        Mark tenant as activated
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            activated_by_user_id: User ID who completed activation
            
        Returns:
            Updated Tenant
        """
        from datetime import datetime
        
        result = await db.execute(
            select(TenantModel).where(TenantModel.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Update tenant status
        tenant.activation_status = 'active'
        tenant.activated_at = datetime.utcnow()
        tenant.activated_by = activated_by_user_id
        tenant.activation_token = None  # Clear token after activation
        
        await db.commit()
        await db.refresh(tenant)
        
        return self._model_to_pydantic(tenant)
    
    def extract_domain_from_email(self, email: str) -> str:
        """
        Extract domain from email address
        
        Args:
            email: Email address
            
        Returns:
            Domain part of the email
        """
        return email.split("@")[1].lower() if "@" in email else ""
    
    def _model_to_pydantic(self, model: TenantModel) -> Tenant:
        """Convert SQLAlchemy model to Pydantic model"""
        return Tenant(
            id=model.id,
            name=model.name,
            domain=model.domain,
            firebase_tenant_id=model.firebase_tenant_id,
            oidc_provider_id=model.oidc_provider_id,
            activation_token=model.activation_token,
            activation_status=model.activation_status,
            activation_expires_at=model.activation_expires_at,
            activated_at=model.activated_at,
            activated_by=model.activated_by,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


# Global tenant service instance
tenant_service = TenantService()
