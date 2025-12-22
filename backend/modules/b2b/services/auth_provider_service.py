"""
Auth Provider Service for B2B tenants

Handles CRUD operations for authentication providers.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import Optional, List

from modules.b2b.models.auth_provider import AuthProvider
from modules.b2b.schemas.auth_provider import (
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
        Now uses domain-specific ID: oidc.{firebase_tenant_id}-web
        """
        from scripts.core.firebase_admin_cli import configure_oidc_provider
        from modules.b2b.schemas.auth_provider import AuthProviderCreate, AuthProviderType
        from modules.b2b.models import TenantModel

        # Fetch tenant to get name for display_name
        tenant = await db.get(TenantModel, tenant_id)
        if not tenant:
             raise ValueError(f"Tenant {tenant_id} not found")

        # 1. Configure in Firebase (GCIP)
        config_to_pass = provider_config.copy()
        if oidc_client_id: config_to_pass['client_id'] = oidc_client_id
        if oidc_client_secret: config_to_pass['client_secret'] = oidc_client_secret
        if oidc_issuer: config_to_pass['issuer'] = oidc_issuer
        if saml_entity_id: config_to_pass['idp_entity_id'] = saml_entity_id
        if saml_sso_url: config_to_pass['sso_url'] = saml_sso_url

        try:
            client_id = config_to_pass.get('client_id')
            client_secret = config_to_pass.get('client_secret')
            issuer = config_to_pass.get('issuer')
            
            if not all([client_id, client_secret, issuer]):
                raise ValueError("Missing required OIDC parameters")
            
            # Use specific ID for Web, ensuring sanitized lowercase
            # firebase_tenant_id usually contains the sanitized domain already
            provider_id = f"oidc.{firebase_tenant_id}-web".lower()
            display_name = f"{tenant.name}-web"

            # Call with individual parameters
            # Use the new ID and Name
            actual_provider_id = configure_oidc_provider(
                firebase_tenant_id,
                provider_type,
                client_id,
                client_secret,
                issuer,
                provider_id_override=provider_id,
                display_name=display_name
            )
        except Exception as e:
            raise Exception(f"Failed to configure provider in Identity Platform: {str(e)}")

        # 2. Create DB Record
        mapped_type = AuthProviderType.OIDC
        if provider_type == 'saml': mapped_type = AuthProviderType.SAML
        elif provider_type == 'google': mapped_type = AuthProviderType.GOOGLE
        elif provider_type == 'microsoft': mapped_type = AuthProviderType.MICROSOFT
        
        stored_config = config_to_pass
        stored_config['issuer'] = stored_config.get('issuer') 
        stored_config['web_provider_id'] = actual_provider_id # Explicitly store web ID

        new_provider_data = AuthProviderCreate(
            tenant_id=tenant_id,
            provider_type=mapped_type,
            provider_id=actual_provider_id,
            display_name=display_name,
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
        issuer: str,
        mobile_client_id: str = None,
        mobile_client_secret: str = None
    ) -> AuthProvider:
        """
        Update existing provider credentials.
        """
        from scripts.core.firebase_admin_cli import configure_oidc_provider
        from sqlalchemy.orm.attributes import flag_modified
        
        # Get the primary provider for this tenant
        provider = await AuthProviderService.get_primary_provider(db, tenant_id)
        
        if not provider:
            raise Exception("No SSO provider configured for this tenant")
        
        # Get tenant information
        from modules.b2b.models import TenantModel
        tenant = await db.get(TenantModel, tenant_id)
        
        if not tenant:
            raise Exception("Tenant not found")
        
        try:
            # 1. Configure WEB Provider
            # Always enforce naming convention for consistency
            web_provider_id = f"oidc.{tenant.firebase_tenant_id}-web".lower()
            
            # Display Name: "{Tenant Name} - Web"
            web_display_name = f"{tenant.name}-web"
            
            print(f"🔧 Configuring Web Provider: {web_provider_id} (Name: {web_display_name})")
            
            configure_oidc_provider(
                firebase_tenant_id=tenant.firebase_tenant_id,
                provider_type=provider.provider_type, 
                client_id=client_id,
                client_secret=client_secret,
                issuer_url=issuer,
                provider_id_override=web_provider_id,
                display_name=web_display_name
            )
            
            # 2. Configure MOBILE Provider (Optional)
            mobile_provider_id = None
            mobile_id = mobile_client_id if mobile_client_id else None
            mobile_secret = mobile_client_secret if mobile_client_secret else None
            
            print(f"🔍 Checking Mobile Config - ClientID: {'***' if mobile_id else 'None'}")
            
            if mobile_id and mobile_secret:
                mobile_provider_id = f"oidc.{tenant.firebase_tenant_id}-mobile".lower()
                mobile_display_name = f"{tenant.name}-mobile"
                
                print(f"🔧 Configuring Mobile Provider: {mobile_provider_id}")
                
                configure_oidc_provider(
                    firebase_tenant_id=tenant.firebase_tenant_id,
                    provider_type=provider.provider_type,
                    client_id=mobile_id,
                    client_secret=mobile_secret,
                    issuer_url=issuer,
                    provider_id_override=mobile_provider_id,
                    display_name=mobile_display_name
                )
            
            # 3. Update DB Record
            provider.provider_id = web_provider_id
            provider.display_name = web_display_name # Update DB display name too
            
            # Ensure config_data is treated as mutable
            if provider.config_data is None:
                provider.config_data = {}
            
            # Use dict copy to ensure mutation is tracked
            updated_config = dict(provider.config_data)
            updated_config.update({
                'client_id': client_id,
                'client_secret': client_secret,
                'issuer': issuer,
                'web_provider_id': web_provider_id 
            })
            
            if mobile_provider_id:
                updated_config['mobile_client_id'] = mobile_id
                updated_config['mobile_client_secret'] = mobile_secret
                updated_config['mobile_provider_id'] = mobile_provider_id
            else:
                updated_config.pop('mobile_client_id', None)
                updated_config.pop('mobile_client_secret', None)
                updated_config.pop('mobile_provider_id', None)
            
            provider.config_data = updated_config
            # FORCE flag_modified for JSONB field
            flag_modified(provider, "config_data")
            
            await db.flush()
            
            # Re-query
            result = await db.execute(
                select(AuthProvider).where(AuthProvider.id == provider.id)
            )
            return result.scalar_one()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to update SSO credentials: {str(e)}")


# Create singleton instance
auth_provider_service = AuthProviderService()
