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
from infrastructure.auth import get_auth_provider
from core.constants import B2BRoleName
from modules.b2b.models import TenantModel, AuthProvider, InvitationModel
from modules.b2b.services.role_template_service import role_template_service
from modules.b2b.services.team_service import create_team
from modules.b2b.services.invitation_service import invitation_service
from modules.b2b.services.invitation_service import invitation_service
from infrastructure.auth import get_tenant_provisioner


class TenantOnboardingService:
    """Service for managing tenant onboarding workflow"""
    
    async def onboard_tenant(
        self,
        db: AsyncSession,
        company_name: str,
        domain: str,
        owner_email: str,
        # New optional params for local/test mode
        tenant_id: Optional[UUID] = None,
        features: Optional[dict] = None,
        subscription_tier: Optional[str] = None
    ) -> dict:
        """
        Complete tenant onboarding workflow (Step 1: Provisioning)
        
        Args:
            db: Database session
            company_name: Company name
            domain: Domain name
            owner_email: Owner email address
            tenant_id: Optional UUID to force a specific tenant ID (for seeding)
            plugins: Optional list of enabled plugins (manual override)
            subscription_tier: Optional tier key (e.g. 'enterprise') to init subscription
        """
        from modules.b2b.models.subscription_plan import B2BSubscriptionPlan
        from modules.b2b.models.subscription import B2BSubscription
        from modules.b2b.services.tenant_service import tenant_service

        try:
            # Initialize Firebase if not already done
            get_auth_provider().initialize()
            
            # Resolve Plan & Features if Tier provided
            target_plan = None
            tier_features = {}
            
            if subscription_tier:
                stmt_plan = select(B2BSubscriptionPlan).where(B2BSubscriptionPlan.tier_key == subscription_tier)
                res_plan = await db.execute(stmt_plan)
                target_plan = res_plan.scalar_one_or_none()
                if target_plan:
                    tier_features = target_plan.features or {}
            
            # Merge features: Plan Features + Manual overrides
            # Using simple update logic (manual overrides plan)
            final_features = tier_features.copy()
            if features:
                # We need a proper merge for 'plugins' list if present in both
                for key, val in features.items():
                    if key == 'plugins' and 'plugins' in final_features:
                         # Union
                         final_features['plugins'] = sorted(list(set(final_features['plugins'] + val)))
                    else:
                         final_features[key] = val
            # Check for existing tenant in DB first to handle idempotency
            stmt = select(TenantModel).where(TenantModel.domain == domain.lower())
            result = await db.execute(stmt)
            existing_tenant = result.scalar_one_or_none()
            
            if existing_tenant:
                if existing_tenant.activation_status == 'active':

                    raise Exception(f"Tenant for domain {domain} is already active.")
                
                print(f"♻️  Tenant exists (pending), resending activation for {domain}")
                
                # Update features if provided (for repair/updating existing demo tenant)
                if final_features:
                     # Use service to ensure hooks run even on repair
                     await tenant_service.update_tenant_features(db, existing_tenant.id, final_features)


                # Update/Ensure Subscription if Tier provided (Repair/Upgrade)
                if target_plan:
                    stmt_sub = select(B2BSubscription).where(B2BSubscription.tenant_id == existing_tenant.id)
                    res_sub = await db.execute(stmt_sub)
                    existing_sub = res_sub.scalar_one_or_none()
                    
                    if existing_sub:
                        # Update if different
                        if existing_sub.tier != target_plan.tier_key:
                             existing_sub.plan_id = target_plan.id
                             existing_sub.tier = target_plan.tier_key
                             # Update prices? Maybe preserve legacy pricing? 
                             # For onboarding/demo fix, verification is key -> Update it.
                             existing_sub.base_price_cents = target_plan.base_price_monthly
                             existing_sub.per_seat_price_cents = target_plan.per_seat_price_monthly
                             existing_sub.total_amount_cents = target_plan.base_price_monthly
                    else:
                        # Create missing subscription
                        new_sub = B2BSubscription(
                             tenant_id=existing_tenant.id,
                             plan_id=target_plan.id,
                             tier=target_plan.tier_key,
                             status='active',
                             seat_count=1,
                             base_price_cents=target_plan.base_price_monthly,
                             per_seat_price_cents=target_plan.per_seat_price_monthly,
                             total_amount_cents=target_plan.base_price_monthly,
                             billing_interval='monthly'
                        )
                        db.add(new_sub)
                
                # Ensure we have an owner invitation to update
                from modules.b2b.models import InvitationModel
                inv_stmt = select(InvitationModel).where(
                    InvitationModel.tenant_id == existing_tenant.id,
                    InvitationModel.role == B2BRoleName.OWNER
                )
                inv_result = await db.execute(inv_stmt)
                invitation = inv_result.scalar_one_or_none()
                
                # Regenerate token if needed or just resend current
                new_token = secrets.token_urlsafe(32)
                expires_at = get_utc_now() + timedelta(hours=48)
                
                existing_tenant.activation_token = new_token
                existing_tenant.activation_expires_at = expires_at
                
                if invitation:
                    invitation.invitation_token = new_token
                    invitation.expires_at = expires_at
                else:
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
            firebase_tenant_id = None # Logic simplified, assuming usually None for local
            if not firebase_tenant_id:
                # Use domain for uniqueness as requested
                provisioner = get_tenant_provisioner()
                firebase_tenant_id = provisioner.create_tenant(company_name, domain)
            
            # 2. Generate activation token
            activation_token = secrets.token_urlsafe(32)
            expires_at = get_utc_now() + timedelta(hours=48)
            
            # 3. Create tenant in database
            tenant_model_args = {
                "name": company_name,
                "domain": domain.lower(),
                "firebase_tenant_id": firebase_tenant_id,
                "activation_token": activation_token,
                "activation_status": 'pending',
                "activation_expires_at": expires_at,
                "is_active": True,
                "is_active": True,
                "features": {} # We set features via service below
            }
            if tenant_id:
                tenant_model_args["id"] = tenant_id
                
            tenant = TenantModel(**tenant_model_args)
            db.add(tenant)
            await db.flush()
            # No refresh yet
            
            # 3.5 Create Subscription if plan found
            if target_plan:
                 sub = B2BSubscription(
                     tenant_id=tenant.id,
                     plan_id=target_plan.id,
                     tier=target_plan.tier_key,
                     status='active',
                     seat_count=1, # Default
                     base_price_cents=target_plan.base_price_monthly,
                     per_seat_price_cents=target_plan.per_seat_price_monthly,
                     total_amount_cents=target_plan.base_price_monthly, # Initial
                     billing_interval='monthly'
                 )
                 db.add(sub)
            else:
                # Fallback to starter if no tier specified? Or leave null? 
                # Better to leave null or create default if business logic requires.
                pass

            # 3.6 Apply Features via Service (Hooks for plugins)
            if final_features:
                await tenant_service.update_tenant_features(db, tenant.id, final_features)

            # 4. Seed roles from templates
            await role_template_service.seed_tenant_roles(db, tenant.id)
            
            # 5. REMOVED: Default Team creation
            # Per "No default team" design principle - owner starts __unassigned__
            # Teams are created explicitly by admin, users assigned to teams as needed
            
            # 8. Create owner invitation (no team assignment - __unassigned__ state)
            admin_invitation = await invitation_service.create_invitation(
                db=db,
                tenant_id=tenant.id,
                email=owner_email,
                role=B2BRoleName.OWNER,
                invitation_token=activation_token,  # Reuse activation token
                team_id=None,  # Owner starts __unassigned__
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
                "activation_url": activation_url,
                "activation_token": activation_token,
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            # await db.rollback() # Logic handled by caller
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
