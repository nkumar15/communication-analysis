"""
Auth Provider Service for B2B tenants

Handles CRUD operations for authentication providers.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import Optional, List

from services.b2b.models.auth_provider import AuthProvider
from services.b2b.schemas.auth_provider import (
    AuthProviderCreate,
    AuthProviderUpdate,
    AuthProviderType
)

class AuthProviderService:
    """Service for managing authentication providers"""
    
    @staticmethod
    async def get_by_id(db: AsyncSession, provider_id: UUID) -> Optional[AuthProvider]:
        """Get auth provider by ID"""
        result = await db.execute(
            select(AuthProvider).where(AuthProvider.id == provider_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_tenant_providers(
        db: AsyncSession, 
        tenant_id: UUID,
        active_only: bool = True
    ) -> List[AuthProvider]:
        """Get all auth providers for a tenant"""
        query = select(AuthProvider).where(AuthProvider.tenant_id == tenant_id)
        
        if active_only:
            query = query.where(AuthProvider.is_active == True)
        
        result = await db.execute(query.order_by(AuthProvider.is_primary.desc(), AuthProvider.created_at))
        return list(result.scalars().all())
    
    @staticmethod
    async def get_primary_provider(
        db: AsyncSession,
        tenant_id: UUID
    ) -> Optional[AuthProvider]:
        """Get the primary auth provider for a tenant"""
        result = await db.execute(
            select(AuthProvider).where(
                and_(
                    AuthProvider.tenant_id == tenant_id,
                    AuthProvider.is_primary == True,
                    AuthProvider.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_provider_id(
        db: AsyncSession,
        tenant_id: UUID,
        provider_id: str
    ) -> Optional[AuthProvider]:
        """Get auth provider by tenant and provider ID"""
        result = await db.execute(
            select(AuthProvider).where(
                and_(
                    AuthProvider.tenant_id == tenant_id,
                    AuthProvider.provider_id == provider_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_provider(
        db: AsyncSession,
        provider_data: AuthProviderCreate
    ) -> AuthProvider:
        """Create a new auth provider"""
        
        # If this is marked as primary, unset other primary providers for this tenant
        if provider_data.is_primary:
            await db.execute(
                select(AuthProvider).where(
                    and_(
                        AuthProvider.tenant_id == provider_data.tenant_id,
                        AuthProvider.is_primary == True
                    )
                )
            )
            # Update existing primary providers
            existing_primaries = (await db.execute(
                select(AuthProvider).where(
                    and_(
                        AuthProvider.tenant_id == provider_data.tenant_id,
                        AuthProvider.is_primary == True
                    )
                )
            )).scalars().all()
            
            for existing in existing_primaries:
                existing.is_primary = False
            await db.flush()
        
        # Create new provider
        provider = AuthProvider(
            tenant_id=provider_data.tenant_id,
            provider_type=provider_data.provider_type.value,
            provider_id=provider_data.provider_id,
            display_name=provider_data.display_name,
            is_primary=provider_data.is_primary,
            is_active=provider_data.is_active,
            config_data=provider_data.config_data
        )
        
        db.add(provider)
        await db.flush()
        await db.refresh(provider)
        
        return provider
    
    @staticmethod
    async def update_provider(
        db: AsyncSession,
        provider_id: UUID,
        update_data: AuthProviderUpdate
    ) -> Optional[AuthProvider]:
        """Update an auth provider"""
        provider = await AuthProviderService.get_by_id(db, provider_id)
        
        if not provider:
            return None
        
        # If setting as primary, unset other primary providers
        if update_data.is_primary and not provider.is_primary:
            existing_primaries = (await db.execute(
                select(AuthProvider).where(
                    and_(
                        AuthProvider.tenant_id == provider.tenant_id,
                        AuthProvider.is_primary == True,
                        AuthProvider.id != provider_id
                    )
                )
            )).scalars().all()
            
            for existing in existing_primaries:
                existing.is_primary = False
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(provider, field, value)
        
        await db.flush()
        await db.refresh(provider)
        
        return provider
    
    @staticmethod
    async def deactivate_provider(
        db: AsyncSession,
        provider_id: UUID
    ) -> bool:
        """Soft delete an auth provider"""
        provider = await AuthProviderService.get_by_id(db, provider_id)
        
        if not provider:
            return False
        
        provider.is_active = False
        await db.flush()
        
        return True


# Create singleton instance
auth_provider_service = AuthProviderService()
