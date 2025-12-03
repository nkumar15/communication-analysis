"""
Platform Tenant Onboarding Service

Handles full tenant provisioning workflow extracted from tenant_onboard.py script.
Includes Firebase tenant creation, OIDC configuration, role seeding, and email notifications.
"""
import secrets
from datetime import timedelta
from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from core.utils import get_utc_now
from core.email import email_service
from core.utils.firebase import firebase_auth_service
from core.constants import B2BRoleName
from services.b2b.models import TenantModel, AuthProvider, InvitationModel
from services.b2b.services.role_template_service import role_template_service
from services.b2b.services.team_service import create_team
from services.b2b.services.invitation_service import invitation_service
from scripts.core.firebase_admin_cli import create_firebase_tenant, configure_oidc_provider


class TenantOnboardingService:
    """Service for managing tenant onboarding workflow"""
    
    async def onboard_tenant(
        self,
        db: AsyncSession,
        company_name: str,
        domain: str,
        owner_email: str,
        oidc_provider: str,
        oidc_client_id: str,
        oidc_client_secret: str,
        oidc_issuer: str
    ) -> dict:
        """
        Complete tenant onboarding workflow
        
        Steps:
        1. Create Firebase tenant
        2. Configure OIDC provider
        3. Generate activation token
        4. Create tenant in database
        5. Seed roles from templates
        6. Create auth provider record
        7. Create default team
        8. Create admin invitation
        9. Send activation email
        
        Args:
            db: Database session
            company_name: Company/tenant name
            domain: Email domain (e.g., acme.com)
            owner_email: Owner/admin email address
            oidc_provider: Provider type (auth0, okta, google, azure)
            oidc_client_id: OIDC client ID
            oidc_client_secret: OIDC client secret
            oidc_issuer: OIDC issuer URL
            
        Returns:
            dict with tenant info, activation URL, and expiration
            
        Raises:
            Exception: If any step fails
        """
        try:
            # Initialize Firebase if not already done
            firebase_auth_service.initialize()
            
            # 1. Create Firebase tenant
            firebase_tenant_id = create_firebase_tenant(company_name)
            
            # 2. Configure OIDC provider
            provider_id = configure_oidc_provider(
                firebase_tenant_id,
                oidc_provider,
                oidc_client_id,
                oidc_client_secret,
                oidc_issuer
            )
            
            # 3. Generate activation token
            activation_token = secrets.token_urlsafe(32)
            expires_at = get_utc_now() + timedelta(hours=48)
            
            # 4. Create tenant in database
            tenant = TenantModel(
                name=company_name,
                domain=domain.lower(),
                firebase_tenant_id=firebase_tenant_id,
                activation_token=activation_token,
                activation_status='pending',
                activation_expires_at=expires_at,
                is_active=True
            )
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
            
            # 5. Seed roles from templates
            await role_template_service.seed_tenant_roles(db, tenant.id)
            
            # 6. Create auth provider record
            auth_provider = AuthProvider(
                tenant_id=tenant.id,
                provider_type='oidc',
                provider_id=provider_id,
                display_name=f"{oidc_provider.title()} SSO",
                is_primary=True,
                is_active=True
            )
            db.add(auth_provider)
            await db.commit()
            
            # 7. Create default team
            default_team = await create_team(
                db=db,
                tenant_id=tenant.id,
                name="Default Team",
                description="Default team for all users",
                is_default=True
            )
            
            # 8. Create admin invitation
            admin_invitation = await invitation_service.create_invitation(
                db=db,
                tenant_id=tenant.id,
                email=owner_email,
                role=B2BRoleName.OWNER,
                invitation_token=activation_token,  # Reuse activation token
                team_id=default_team.id,
                expires_in_days=2  # 48 hours
            )
            
            # 9. Send activation email
            frontend_url = settings.frontend_url or "http://localhost:3000"
            activation_url = f"{frontend_url}/activate/{activation_token}"
            
            email_service.send_activation_email(
                owner_email,
                company_name,
                activation_url,
                expires_at
            )
            
            return {
                "tenant_id": str(tenant.id),
                "tenant_name": company_name,
                "domain": domain,
                "owner_email": owner_email,
                "firebase_tenant_id": firebase_tenant_id,
                "oidc_provider_id": provider_id,
                "activation_url": activation_url,
                "activation_token": activation_token,
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            await db.rollback()
            raise Exception(f"Tenant onboarding failed: {str(e)}")
    
    
    async def resend_activation(
        self,
        db: AsyncSession,
        tenant_id: UUID
    ) -> dict:
        """
        Regenerate activation token and resend activation email
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            
        Returns:
            dict with new activation URL and expiration
            
        Raises:
            Exception: If tenant not found or already activated
        """
        # Get tenant
        tenant = await db.get(TenantModel, tenant_id)
        if not tenant:
            raise Exception(f"Tenant {tenant_id} not found")
        
        if tenant.activation_status == 'active':
            raise Exception("Tenant is already activated")
        
        # Generate new token
        new_token = secrets.token_urlsafe(32)
        new_expires_at = get_utc_now() + timedelta(hours=48)
        
        # Update tenant
        tenant.activation_token = new_token
        tenant.activation_expires_at = new_expires_at
        tenant.activation_status = 'pending'  # Reset if expired
        
        await db.commit()
        
        # Get admin invitation to resend email
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.tenant_id == tenant_id)
            .where(InvitationModel.role == B2BRoleName.OWNER)
            .order_by(InvitationModel.created_at.desc())
            .limit(1)
        )
        invitation = result.scalar_one_or_none()
        
        if invitation:
            # Update invitation token too
            invitation.invitation_token = new_token
            invitation.expires_at = new_expires_at
            await db.commit()
            
            # Resend email
            frontend_url = settings.frontend_url or "http://localhost:3000"
            activation_url = f"{frontend_url}/activate/{new_token}"
            
            email_service.send_activation_email(
                invitation.email,
                tenant.name,
                activation_url,
                new_expires_at
            )
        
        return {
            "tenant_id": str(tenant_id),
            "activation_url": f"{settings.frontend_url or 'http://localhost:3000'}/activate/{new_token}",
            "expires_at": new_expires_at.isoformat()
        }


# Singleton instance
tenant_onboarding_service = TenantOnboardingService()
