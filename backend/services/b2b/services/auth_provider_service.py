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
            select(AuthProvider)
            .where(AuthProvider.id == provider_id)
            .where(AuthProvider.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_tenant_providers(
        db: AsyncSession, 
        tenant_id: UUID,
        active_only: bool = True
    ) -> List[AuthProvider]:
        """Get all auth providers for a tenant"""
        query = select(AuthProvider).where(AuthProvider.tenant_id == tenant_id).where(AuthProvider.deleted_at.is_(None))
        
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
                    AuthProvider.is_active == True,
                    AuthProvider.deleted_at.is_(None)
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
                    AuthProvider.provider_id == provider_id,
                    AuthProvider.deleted_at.is_(None)
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
                        AuthProvider.is_primary == True,
                        AuthProvider.deleted_at.is_(None)
                    )
                )
            )
            # Update existing primary providers
            existing_primaries = (await db.execute(
                select(AuthProvider).where(
                    and_(
                        AuthProvider.tenant_id == provider_data.tenant_id,
                        AuthProvider.is_primary == True,
                        AuthProvider.deleted_at.is_(None)
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
        # Re-query instead of refresh (RLS-compatible)
        result = await db.execute(select(AuthProvider).where(AuthProvider.id == provider.id))
        provider = result.scalar_one()
        
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
                        AuthProvider.id != provider_id,
                        AuthProvider.deleted_at.is_(None)
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
        # Re-query instead of refresh (RLS-compatible)
        result = await db.execute(select(AuthProvider).where(AuthProvider.id == provider.id))
        provider = result.scalar_one()
        
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

    @staticmethod
    async def setup_initial_provider(
        db: AsyncSession,
        tenant_id: UUID,
        firebase_tenant_id: str,
        provider_type: str,
        provider_config: dict,
        oidc_client_id: Optional[str] = None,
        oidc_client_secret: Optional[str] = None,
        oidc_issuer: Optional[str] = None,
        saml_entity_id: Optional[str] = None,
        saml_sso_url: Optional[str] = None
    ) -> AuthProvider:
        """
        Setup the initial Auth Provider during tenant activation.
        
        1. Configures the provider in Firebase/GCIP.
        2. Creates the AuthProvider record in the DB.
        """
        from scripts.core.firebase_admin_cli import configure_oidc_provider
        from services.b2b.schemas.auth_provider import AuthProviderCreate, AuthProviderType
        
        # 1. Configure in Firebase (GCIP)
        # Note: We reuse the existing CLI helper logic for now to keep it DRY.
        # It handles OIDC logic. For SAML, we might need to extend it later or here.
        
        # Construct arguments expected by configure_oidc_provider
        # It expects specific args or a config dict wrapper? 
        # Let's check imports. It takes (firebase_tenant_id, provider_type, config)
        
        # Mapping frontend 'provider_type' to internal enum/string
        # 'oidc', 'google', 'microsoft' -> handled by configure_oidc_provider
        
        # Prepare standard config dict for the helper
        config_to_pass = provider_config.copy()
        if oidc_client_id: config_to_pass['client_id'] = oidc_client_id
        if oidc_client_secret: config_to_pass['client_secret'] = oidc_client_secret
        if oidc_issuer: config_to_pass['issuer'] = oidc_issuer
        if saml_entity_id: config_to_pass['idp_entity_id'] = saml_entity_id
        if saml_sso_url: config_to_pass['sso_url'] = saml_sso_url

        try:
            # Extract individual parameters from config
            client_id = config_to_pass.get('client_id')
            client_secret = config_to_pass.get('client_secret')
            issuer = config_to_pass.get('issuer')
            
            if not all([client_id, client_secret, issuer]):
                raise ValueError("Missing required OIDC parameters: client_id, client_secret, and issuer")
            
            # Call with individual parameters as expected by function signature
            provider_id = configure_oidc_provider(
                firebase_tenant_id,
                provider_type,
                client_id,
                client_secret,
                issuer
            )
        except Exception as e:
            raise Exception(f"Failed to configure provider in Identity Platform: {str(e)}")

        # 2. Create DB Record
        # Determine strict enum type
        mapped_type = AuthProviderType.OIDC
        if provider_type == 'saml': mapped_type = AuthProviderType.SAML
        elif provider_type == 'google': mapped_type = AuthProviderType.GOOGLE
        elif provider_type == 'microsoft': mapped_type = AuthProviderType.MICROSOFT
        
        # Store comprehensive config in JSON
        stored_config = config_to_pass
        stored_config['issuer'] = stored_config.get('issuer') # Ensure issuer is there for OIDC
        
        new_provider_data = AuthProviderCreate(
            tenant_id=tenant_id,
            provider_type=mapped_type,
            provider_id=provider_id,
            display_name=f"{provider_type.upper()} Login",
            is_primary=True,
            is_active=True,
            config_data=stored_config
        )
        
        return await AuthProviderService.create_provider(db, new_provider_data)

    @staticmethod
    async def update_provider_credentials(
        db: AsyncSession,
        tenant_id: UUID,
        client_id: str,
        client_secret: str,
        issuer: str
    ) -> AuthProvider:
        """
        Update existing provider credentials (post-activation reconfiguration).
        
        1. Updates credentials in Firebase/GCIP
        2. Updates AuthProvider record in DB
        """
        from scripts.core.firebase_admin_cli import configure_oidc_provider
        
        # Get the primary provider for this tenant
        provider = await AuthProviderService.get_primary_provider(db, tenant_id)
        
        if not provider:
            raise Exception("No SSO provider configured for this tenant")
        
        # Get tenant to retrieve firebase_tenant_id
        from services.b2b.models import TenantModel
        tenant = await db.get(TenantModel, tenant_id)
        
        if not tenant:
            raise Exception("Tenant not found")
        
        try:
            # Update in Firebase/GCIP
            configure_oidc_provider(
                tenant.firebase_tenant_id,
                provider.provider_type,
                client_id,
                client_secret,
                issuer,
                provider_id_override=provider.provider_id  # Keep same provider ID
            )
            
            # Update config_data in DB
            updated_config = provider.config_data or {}
            updated_config.update({
                'client_id': client_id,
                'client_secret': client_secret,
                'issuer': issuer
            })
            
            provider.config_data = updated_config
            await db.flush()
            
            # Re-query to get updated record
            result = await db.execute(
                select(AuthProvider).where(AuthProvider.id == provider.id)
            )
            return result.scalar_one()
            
        except Exception as e:
            raise Exception(f"Failed to update SSO credentials: {str(e)}")


# Create singleton instance
auth_provider_service = AuthProviderService()
