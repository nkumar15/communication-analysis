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
from infrastructure.email import email_service
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
        # New optional params for local/test mode
        firebase_tenant_id: Optional[str] = None
    ) -> dict:
        """
        Complete tenant onboarding workflow (Step 1: Provisioning)
        
        Args:
            db: Database session
            company_name: Company name
            domain: Domain name
            owner_email: Owner email address
            firebase_tenant_id: Optional existing Firebase tenant ID (skips creation if provided)
        """

        try:
            # Initialize Firebase if not already done
            firebase_auth_service.initialize()
            
            # Check for existing tenant in DB first to handle idempotency
            stmt = select(TenantModel).where(TenantModel.domain == domain.lower())
            result = await db.execute(stmt)
            existing_tenant = result.scalar_one_or_none()
            
            if existing_tenant:
                if existing_tenant.activation_status == 'active':
                    raise Exception(f"Tenant for domain {domain} is already active.")
                
                # If pending/inactive, we treat this as a resend/repair
                print(f"♻️  Tenant exists (pending), resending activation for {domain}")
                # Use existing logic to resend
                # We return the existing tenant details to the caller
                
                # Ensure we have an owner invitation to update
                from services.b2b.models import InvitationModel
                inv_stmt = select(InvitationModel).where(
                    InvitationModel.tenant_id == existing_tenant.id,
                    InvitationModel.role == B2BRoleName.OWNER
                )
                inv_result = await db.execute(inv_stmt)
                invitation = inv_result.scalar_one_or_none()
                
                # Regenerate token if needed or just resend current
                # Let's verify if we need to call resend_activation logic
                # For simplicity, we can just call self.resend_activation logic here or reuse code
                
                # Update expiration
                new_token = secrets.token_urlsafe(32)
                expires_at = get_utc_now() + timedelta(hours=48)
                
                existing_tenant.activation_token = new_token
                existing_tenant.activation_expires_at = expires_at
                
                if invitation:
                    invitation.invitation_token = new_token
                    invitation.expires_at = expires_at
                else:
                     # Create missing invitation if it got lost?
                     pass 

                await db.flush()
                
                # Send email
                frontend_url = settings.frontend_url or "http://localhost:3000"
                activation_url = f"{frontend_url}/activate/{new_token}"
                
                email_service.send_activation_email(
                    owner_email,
                    company_name,
                    activation_url,
                    expires_at
                )

                return {
                    "tenant_id": str(existing_tenant.id),
                    "tenant_name": existing_tenant.name,
                    "domain": existing_tenant.domain,
                    "owner_email": owner_email,
                    "firebase_tenant_id": existing_tenant.firebase_tenant_id,
                    "activation_url": activation_url,
                    "activation_token": new_token,
                    "expires_at": expires_at.isoformat()
                }

            # 1. Create OR Use Firebase tenant
            if not firebase_tenant_id:
                # Use domain for uniqueness as requested
                firebase_tenant_id = create_firebase_tenant(company_name, domain)
            
            # 2. Generate activation token
            activation_token = secrets.token_urlsafe(32)
            expires_at = get_utc_now() + timedelta(hours=48)
            
            # 3. Create tenant in database
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
            await db.flush()
            await db.refresh(tenant)
            
            # 4. Seed roles from templates
            await role_template_service.seed_tenant_roles(db, tenant.id)
            
            # 5. Create default team (auth provider creation moved to activation phase)
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
            
            # Commit handled by caller
            # await db.commit()
            
            return {
                "tenant_id": str(tenant.id),
                "tenant_name": company_name,
                "domain": domain,
                "owner_email": owner_email,
                "firebase_tenant_id": firebase_tenant_id,
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
        
        await db.flush()
        
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
            await db.flush()
            
            # Resend email
            frontend_url = settings.frontend_url or "http://localhost:3000"
            activation_url = f"{frontend_url}/activate/{new_token}"
            
            email_service.send_activation_email(
                invitation.email,
                tenant.name,
                activation_url,
                new_expires_at
            )
        
        # Commit handled by caller
        # await db.commit()
        
        return {
            "tenant_id": str(tenant_id),
            "activation_url": f"{settings.frontend_url or 'http://localhost:3000'}/activate/{new_token}",
            "expires_at": new_expires_at.isoformat()
        }


# Singleton instance
tenant_onboarding_service = TenantOnboardingService()
