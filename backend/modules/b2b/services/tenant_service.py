from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from modules.b2b.models import TenantModel
from modules.b2b.schemas import Tenant
from modules.b2b.services.role_template_service import role_template_service
from core.utils import get_utc_now


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
            .where(TenantModel.deleted_at.is_(None))
        )
        tenant_model = result.scalar_one_or_none()
        
        if not tenant_model:
            return None
        
        return self._model_to_pydantic(tenant_model)
    
    async def get_tenant_by_domain_include_inactive(self, db: AsyncSession, domain: str) -> Optional[Tenant]:
        """
        Get tenant by email domain, including inactive (deactivated) tenants.
        Used to provide specific error messages for deactivated organizations.
        """
        result = await db.execute(
            select(TenantModel)
            .where(TenantModel.domain == domain.lower())
            .where(TenantModel.deleted_at.is_(None))  # Not hard-deleted
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
            .where(TenantModel.deleted_at.is_(None))
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
            
        Note: Does NOT filter by is_active to allow middleware to check activation_status
        """
        result = await db.execute(
            select(TenantModel)
            .where(TenantModel.firebase_tenant_id == firebase_tenant_id)
            .where(TenantModel.deleted_at.is_(None))  # Only exclude soft-deleted
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
            .where(TenantModel.deleted_at.is_(None))
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
        
        result = await db.execute(
            select(TenantModel).where(TenantModel.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Update tenant status
        tenant.activation_status = 'active'
        tenant.activated_at = get_utc_now()
        tenant.activated_by = activated_by_user_id
        tenant.activation_token = None  # Clear token after activation
        
        await db.flush()
        # Re-query instead of refresh (RLS-compatible)
        result = await db.execute(select(TenantModel).where(TenantModel.id == tenant.id))
        tenant = result.scalar_one()
        
        return self._model_to_pydantic(tenant)
    
    async def delete_tenant(self, db: AsyncSession, tenant_id: UUID) -> bool:
        """
        Soft delete a tenant
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            
        Returns:
            True if deleted, False if not found
        """
        
        result = await db.execute(
            select(TenantModel)
            .where(TenantModel.id == tenant_id)
            .where(TenantModel.deleted_at.is_(None))
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            return False
            
        tenant.deleted_at = get_utc_now()
        tenant.is_active = False
        
        await db.flush()
        return True
    
    async def validate_activation_token(
        self,
        db: AsyncSession,
        token: str
    ) -> dict:
        """
        Validate activation token and return tenant/invitation info
        
        Returns dict with tenant_id, tenant_name, domain, admin_email, expires_at
        Raises HTTPException if invalid
        """
        from fastapi import HTTPException, status
        from modules.b2b.services.invitation_service import invitation_service
        from core.db.rls import rls_service
        from datetime import datetime, timezone
        
        # Get tenant by activation token
        tenant = await self.get_tenant_by_activation_token(db, token)
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid activation token"
            )
        
        # Check expiry
        now_utc = datetime.now(timezone.utc)
        if tenant.activation_expires_at and tenant.activation_expires_at < now_utc:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Activation token has expired"
            )
        
        # Check not already activated
        if tenant.activation_status == 'active':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant is already activated"
            )
        
        # Set RLS context to allow reading protected invitation
        await rls_service.set_tenant_context(db, tenant.id)
        
        # Get invitation for admin email
        invitation = await invitation_service.get_invitation_by_token(db, token)
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        return {
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "domain": tenant.domain,
            "admin_email": invitation.email,
            "expires_at": tenant.activation_expires_at
        }
    
    async def get_activation_tenant_info(
        self,
        db: AsyncSession,
        tenant_id: UUID
    ) -> dict:
        """
        Get tenant info for SSO configuration during activation
        
        Returns dict with firebase_tenant_id, oidc_provider_id, etc.
        Raises HTTPException if not found
        """
        from fastapi import HTTPException, status
        from modules.b2b.services.auth_provider_service import auth_provider_service
        
        tenant = await self.get_tenant_by_id(db, tenant_id)
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Get primary auth provider
        primary_provider = await auth_provider_service.get_primary_provider(db, tenant.id)
        
        # Get mobile specific provider ID if available
        mobile_provider_id = None
        if primary_provider and primary_provider.config_data:
            mobile_provider_id = primary_provider.config_data.get('mobile_provider_id')
        
        return {
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "firebase_tenant_id": tenant.firebase_tenant_id,
            "oidc_provider_id": primary_provider.provider_id if primary_provider else None,
            "mobile_oidc_provider_id": mobile_provider_id,
            "provider_type": primary_provider.provider_type if primary_provider else 'oidc'
        }
    
    async def complete_tenant_activation(
        self,
        db: AsyncSession,
        activation_token: str,
        firebase_uid: str
    ) -> dict:
        """
        Complete tenant activation workflow
        
        Returns dict with message, tenant_id, tenant_name
        Raises HTTPException if validation fails
        """
        from fastapi import HTTPException, status
        from modules.b2b.services.invitation_service import invitation_service
        from modules.b2b.services.user_service import user_service
        from core.db.rls import rls_service
        from core.constants import B2BRoleName
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import select
        from modules.b2b.models import TenantModel
        
        # Get tenant with atomic locking (NO RLS - tenants is global)
        result = await db.execute(
            select(TenantModel)
            .where(TenantModel.activation_token == activation_token)
            .with_for_update()  # Lock row to prevent race conditions
        )
        tenant_model = result.scalar_one_or_none()
        
        if not tenant_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid activation token"
            )
        
        # Check if activation already started (prevents replay attacks)
        if tenant_model.activation_started_at:
            # Allow a grace period of 5 minutes in case of legitimate retries
            grace_period = timedelta(minutes=5)
            time_since_start = datetime.now(timezone.utc) - tenant_model.activation_started_at
            
            if time_since_start > grace_period:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Activation already in progress or completed"
                )
        else:
            # Mark activation as started (prevents concurrent attempts)
            tenant_model.activation_started_at = datetime.now(timezone.utc)
            await db.flush()
        
        # Set RLS context for this tenant (required for user/invitation queries)
        await rls_service.set_tenant_context(db, tenant_model.id)
        
        # Get user from database (with RLS context set)
        user = await user_service.get_user_by_firebase_uid(db, tenant_model.id, firebase_uid)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not found for this tenant"
            )
        
        # Verify user has owner or admin role
        if user.role not in [B2BRoleName.OWNER, B2BRoleName.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners or admins can activate tenants"
            )
        
        # Verify email matches the invitation
        invitation = await invitation_service.get_invitation_by_token(db, activation_token)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found or already accepted"
            )
        
        if user.email != invitation.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User email does not match the invitation email"
            )
        
        # Mark invitation as accepted
        await invitation_service.accept_invitation(db, activation_token)
        
        # Activate tenant
        await self.activate_tenant(db, tenant_model.id, user.id)
        
        return {
            "message": "Tenant activated successfully",
            "tenant_id": str(tenant_model.id),
            "tenant_name": tenant_model.name
        }
    
    async def check_activation_status(
        self,
        db: AsyncSession,
        token: str
    ) -> dict:
        """
        Check activation status
        
        Returns dict with status, message, user_created
        """
        from modules.b2b.services.invitation_service import invitation_service
        from core.db.rls import rls_service
        from sqlalchemy import select
        from modules.b2b.models import UserModel
        
        # Query tenant (NO RLS - tenants is a global table)
        tenant = await self.get_tenant_by_activation_token(db, token)
        
        if not tenant:
            return {"status": "invalid", "message": "Invalid activation token", "user_created": False}
        
        # Set RLS context to query invitation (RLS-protected table)
        await rls_service.set_tenant_context(db, tenant.id)
        
        # Check if invitation exists and get admin email
        invitation = await invitation_service.get_invitation_by_token(db, token)
        
        if not invitation:
            return {"status": "invalid", "message": "Invitation not found", "user_created": False}
        
        # Check if user has been created (SSO login completed)
        result = await db.execute(
            select(UserModel)
            .where(UserModel.tenant_id == tenant.id)
            .where(UserModel.email == invitation.email)
            .where(UserModel.is_active == True)
        )
        user = result.scalar_one_or_none()
        
        if user:
            return {
                "status": "ready",
                "message": "SSO login successful, ready to complete activation",
                "user_created": True
            }
        else:
            return {
                "status": "pending",
                "message": "Waiting for SSO login",
                "user_created": False
            }
    
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
            activation_token=model.activation_token,
            activation_status=model.activation_status,
            activation_expires_at=model.activation_expires_at,
            activated_at=model.activated_at,
            activated_by=model.activated_by,
            activation_started_at=model.activation_started_at,
            is_active=model.is_active,
            domain_type=getattr(model, 'domain_type', 'default'),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


    async def get_billing_profile(self, db: AsyncSession, tenant_id: UUID) -> dict:
        """
        Get tenant billing profile
        """
        tenant = await db.get(TenantModel, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Helper to extract address string from JSONB
        addr_str = None
        if tenant.billing_address:
            if isinstance(tenant.billing_address, dict):
                 addr_str = tenant.billing_address.get('text', '') or tenant.billing_address.get('address', '')
            elif isinstance(tenant.billing_address, str):
                addr_str = tenant.billing_address
        
        return {
            "tax_id": tenant.tax_id,
            "vat_number": tenant.vat_number,
            "billing_address": addr_str,
            "billing_email": tenant.billing_email
        }
    
    async def update_billing_profile(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        tax_id: Optional[str] = None,
        vat_number: Optional[str] = None,
        billing_address: Optional[str] = None,
        billing_email: Optional[str] = None
    ) -> dict:
        """
        Update tenant billing profile
        """
        tenant = await db.get(TenantModel, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        if tax_id is not None: tenant.tax_id = tax_id
        if vat_number is not None: tenant.vat_number = vat_number
        
        if billing_address is not None: 
            # Store as structured JSON
            tenant.billing_address = {"text": billing_address}
            
        if billing_email is not None: tenant.billing_email = billing_email
        
        await db.flush()
        
        return await self.get_billing_profile(db, tenant_id)

    async def setup_initial_sso(
        self,
        db: AsyncSession,
        activation_token: str,
        provider_type: str,
        provider_config: dict,
        oidc_client_id: Optional[str] = None,
        oidc_client_secret: Optional[str] = None,
        oidc_issuer: Optional[str] = None,
        saml_entity_id: Optional[str] = None,
        saml_sso_url: Optional[str] = None
    ) -> dict:
        """
        Setup initial SSO provider (moved from activation router)
        """
        from modules.b2b.services.auth_provider_service import auth_provider_service
        
        # 1. Validate Token to get Tenant
        validation = await self.validate_activation_token(db, activation_token)
        tenant_id = validation["tenant_id"]
        
        tenant = await db.get(TenantModel, tenant_id)
        if not tenant:
             raise ValueError("Tenant not found")
             
        if tenant.activation_status != 'pending':
             raise ValueError("Tenant is not in pending activation state")

        # 2. Setup Provider
        provider = await auth_provider_service.setup_initial_provider(
            db=db,
            tenant_id=tenant_id,
            firebase_tenant_id=tenant.firebase_tenant_id,
            provider_type=provider_type,
            provider_config=provider_config,
            oidc_client_id=oidc_client_id,
            oidc_client_secret=oidc_client_secret,
            oidc_issuer=oidc_issuer,
            saml_entity_id=saml_entity_id,
            saml_sso_url=saml_sso_url
        )
        
        return {
            "success": True,
            "provider_id": provider.provider_id,
            "message": "SSO configured successfully"
        }


    async def update_tenant_plugins(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        new_plugin_list: list[str]
    ) -> dict:
        """
        Update tenant plugins with lifecycle hooks.
        Calculates diff, runs enable/disable hooks, and updates DB.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            new_plugin_list: List of plugin names that SHOULD be active
            
        Returns:
            Dict with added and removed, and current active list
        """
        from core.rbac.plugin_registry import plugin_registry
        from sqlalchemy.orm.attributes import flag_modified
        
        tenant = await db.get(TenantModel, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        old_plugins = set(tenant.plugins or [])
        new_plugins = set(new_plugin_list)
        
        added = new_plugins - old_plugins
        removed = old_plugins - new_plugins

        added = new_plugins - old_plugins
        removed = old_plugins - new_plugins

        # 1. Run Enable Hooks (Additions)
        for plugin_name in added:
            plugin = plugin_registry.get_plugin(plugin_name)
            if plugin:

                # Idempotent seed/init
                try:
                    await plugin.on_tenant_enable(str(tenant_id), db)
                except Exception as e:
                    # If hook fails, we should probably abort the whole transaction to be safe?
                    # Or log and continue? Safe approach -> abort.
                    raise Exception(f"Failed to enable plugin {plugin_name}: {str(e)}")
            else:
                # Warning: Enabling a plugin that isn't registered in the code
                # This might happen if code is old but config is new, or plugin removed.
                pass

        # 2. Run Disable Hooks (Removals)
        for plugin_name in removed:
            plugin = plugin_registry.get_plugin(plugin_name)
            if plugin:
                try:
                    await plugin.on_tenant_disable(str(tenant_id), db)
                except Exception as e:
                    # Log error but proceed with disabling?
                    # Usually better to fail loudly.
                    raise Exception(f"Failed to disable plugin {plugin_name}: {str(e)}")

        # 3. Update DB
        if added or removed:
            tenant.plugins = sorted(list(new_plugins))
            flag_modified(tenant, 'plugins')
            await db.flush()
        
        return {
            "tenant_id": str(tenant_id),
            "added": sorted(list(added)),
            "removed": sorted(list(removed)),
            "active_plugins": sorted(list(new_plugins))
        }


# Global tenant service instance
tenant_service = TenantService()
