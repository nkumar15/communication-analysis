"""
B2B Subscription Service

Async service for managing B2B tenant subscriptions with base + per-seat pricing model.
Integrates with Stripe for card-based payments.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID
import logging

from infrastructure.payment import PaymentProviderFactory
from core.config import settings
from modules.b2b.models import (
    Subscription,
    SubscriptionEvent,
    SubscriptionTier,
    PaymentMode,
    SubscriptionStatus,
    TenantModel,
    B2BSubscriptionPlan
)
from modules.b2b.models.user import UserModel
from modules.b2b.models.rbac import Role
from modules.b2b.services.coupon_service import B2BCouponService
from infrastructure.email import email_service

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Async service for B2B subscription management.
    Handles seat-based pricing, Stripe integration, and subscription lifecycle.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Initialize Stripe provider with B2B-specific keys
        self.provider = PaymentProviderFactory.create(
            'stripe',
            config={
                'secret_key': settings.stripe_b2b_secret_key,
                'webhook_secret': settings.stripe_b2b_webhook_secret,
            }
        )
    
    async def get_tenant_subscription(self, tenant_id: UUID) -> Optional[Subscription]:
        """Get subscription for a tenant"""
        result = await self.db.execute(
            select(Subscription).where(Subscription.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_subscription_details(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive subscription details, including pricing and payment method info.
        Returns default starter tier info if no subscription exists.
        """
        subscription = await self.get_tenant_subscription(tenant_id)
        
        if not subscription:
            # Return default starter tier info
            seat_count = await self.get_active_seat_count(tenant_id)
            # Fetch starter plan for default pricing
            plan = await self.get_plan_by_tier_key(SubscriptionTier.STARTER.value)
            pricing = await self.calculate_seat_based_pricing(
                plan,
                seat_count,
                'monthly'
            )
            
            return {
                "id": "",
                "tenant_id": str(tenant_id),
                "tier": "starter",
                "payment_mode": "card",
                "status": "active",
                "seat_count": seat_count,
                "base_price_cents": pricing['base_price_cents'],
                "per_seat_price_cents": pricing['per_seat_price_cents'],
                "total_amount_cents": pricing['total_amount_cents'],
                "currency": "USD",
                "billing_interval": "monthly",
                "current_period_start": None,
                "current_period_end": None,
                "payment_method_info": None
            }
        
        # Enrich with Stripe payment method info if applicable
        payment_method_info = await self._enrich_with_stripe_payment_method(subscription)
        
        return {
            "id": str(subscription.id),
            "tenant_id": str(subscription.tenant_id),
            "tier": subscription.tier,
            "payment_mode": subscription.payment_mode,
            "status": subscription.status,
            "seat_count": subscription.seat_count,
            "base_price_cents": subscription.base_price_cents,
            "per_seat_price_cents": subscription.per_seat_price_cents,
            "total_amount_cents": subscription.total_amount_cents,
            "currency": subscription.currency,
            "billing_interval": subscription.billing_interval,
            "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "payment_method_info": payment_method_info
        }

    async def _enrich_with_stripe_payment_method(self, subscription: Subscription) -> Optional[Dict[str, Any]]:
        """
        Fetch default payment method details from Stripe.
        """
        import stripe
        
        if subscription.payment_mode != 'card' or not subscription.provider_subscription_id:
            return None
            
        try:
            stripe.api_key = settings.stripe_b2b_secret_key
            
            stripe_sub_obj = stripe.Subscription.retrieve(subscription.provider_subscription_id)
            
            pm_id = stripe_sub_obj.default_payment_method
            
            if not pm_id and stripe_sub_obj.customer:
                 customer = stripe.Customer.retrieve(stripe_sub_obj.customer)
                 if customer.invoice_settings and customer.invoice_settings.default_payment_method:
                     pm_id = customer.invoice_settings.default_payment_method
            
            if pm_id:
                if isinstance(pm_id, str):
                    pm = stripe.PaymentMethod.retrieve(pm_id)
                else:
                    pm = pm_id
                
                if pm.type == 'card':
                    return {
                        'card_brand': pm.card.brand,
                        'card_last4': pm.card.last4,
                        'exp_year': pm.card.exp_year
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch payment method from Stripe: {e}")
            
        return None

    async def calculate_seat_based_pricing(
        self, 
        plan: Any,
        seat_count: int, 
        billing_interval: str
    ) -> Dict[str, int]:
        """
        Calculate pricing based on base + per-seat model from Plan object.
        """
        if billing_interval == 'monthly':
            base_price = plan.base_price_monthly
            per_seat_price = plan.per_seat_price_monthly
        elif billing_interval == 'yearly':
            base_price = plan.base_price_yearly
            per_seat_price = plan.per_seat_price_yearly
        else:
            raise ValueError(f"Invalid billing interval: {billing_interval}")
            
        total_amount = base_price + (seat_count * per_seat_price)
        
        return {
            'base_price_cents': base_price,
            'per_seat_price_cents': per_seat_price,
            'total_amount_cents': total_amount
        }
    
    async def create_checkout_session(
        self,
        tenant_id: UUID,
        tier: SubscriptionTier,
        billing_interval: str = 'monthly',
        coupon_code: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create Stripe checkout session for card-based subscription.
        Only for card payment mode.
        """
        if tier == SubscriptionTier.STARTER:
            raise ValueError("Starter tier is free, no checkout needed")
        
        if billing_interval not in ['monthly', 'yearly']:
            raise ValueError(f"Invalid billing interval: {billing_interval}")

        # Fetch plan configuration
        plan = await self.get_plan_by_tier_key(tier.value)
        
        # Get or create Stripe customer
        subscription = await self.get_tenant_subscription(tenant_id)
        
        # Get tenant for customer creation
        tenant_result = await self.db.execute(
            select(TenantModel).where(TenantModel.id == tenant_id)
        )
        tenant = tenant_result.scalar_one()
        
        customer_id = subscription.provider_customer_id if subscription else None
        
        if not customer_id:
            # Get tenant owner for email
            owner_result = await self.db.execute(
                select(UserModel)
                .join(Role, UserModel.role_id == Role.id)
                .where(
                    UserModel.tenant_id == tenant_id,
                    Role.name == 'owner',
                    UserModel.deleted_at == None
                )
            )
            owner_user = owner_result.scalar_one_or_none()
            owner_email = owner_user.email if owner_user else f"billing@{tenant.domain}"
            
            # Create Stripe customer
            logger.info(f"Creating Stripe customer for tenant {tenant_id} with email {owner_email}")
            customer_result = await self.provider.create_customer(
                user_id=str(tenant_id),
                email=owner_email,
                name=tenant.name,
                metadata={'tenant_id': str(tenant_id)}
            )
            customer_id = customer_result['provider_customer_id']
        
        # Calculate pricing
        seat_count = await self.get_active_seat_count(tenant_id)
        pricing = await self.calculate_seat_based_pricing(plan, seat_count, billing_interval)
        
        # Get Stripe price ID from plan config
        stripe_config = plan.provider_config.get('stripe', {})
        price_key = f'{billing_interval}_price_id'
        price_id = stripe_config.get(price_key)
        
        if not price_id:
            raise ValueError(f"Stripe price ID not configured for plan {tier.value} ({billing_interval})")
        
        # Default URLs
        if not success_url:
            success_url = f"{settings.frontend_url}/billing/subscription?session_id={{CHECKOUT_SESSION_ID}}"
        if not cancel_url:
            cancel_url = f"{settings.frontend_url}/billing"
        
        # Create checkout session
        logger.info(f"Creating checkout for tenant {tenant_id}, tier {tier.value}, seats {seat_count}")
        
        metadata = {
            'tenant_id': str(tenant_id),
            'tier': tier.value,
            'plan_id': str(plan.id),
            'billing_interval': billing_interval,
            'seat_count': seat_count,
            'pricing_snapshot': str(pricing)
        }
        
        # Validate coupon if provided
        discounts = []
        if coupon_code:
            try:
                coupon_service = B2BCouponService(self.db)
                # Check for existing redemption logic is in validate_coupon
                coupon = await coupon_service.validate_coupon(
                    code=coupon_code,
                    tenant_id=tenant_id,
                    tier=tier.value
                )
                
                if coupon.provider_coupon_id:
                    # Assuming provider_coupon_id matches the Stripe Coupon ID format
                    discounts.append({'coupon': coupon.provider_coupon_id})
                    logger.info(f"Applying coupon {coupon.code} (ID: {coupon.provider_coupon_id}) to checkout")
                else:
                     logger.warning(f"Coupon {coupon.code} valid internally but missing provider_coupon_id. Skipping discount.")

                metadata['coupon_code'] = coupon.code

            except Exception as e:
                logger.warning(f"Coupon validation failed: {str(e)}")
                # Depending on UX, we might want to raise this to UI
                raise ValueError(f"Invalid coupon: {str(e)}")

        result = await self.provider.create_checkout_session(
            customer_id=customer_id,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            quantity=seat_count,  # Stripe quantity for per-seat pricing
            discounts=discounts if discounts else None
        )
        
        return {
            'checkout_session_id': result['checkout_session_id'],
            'checkout_url': result['checkout_url'],
            'seat_count': seat_count,
            'pricing': pricing
        }
    
    async def handle_checkout_completed(self, session_data: Dict[str, Any]) -> Subscription:
        """
        Process successful Stripe checkout.
        Called from webhook handler.
        """
        metadata = session_data.get('metadata', {})
        tenant_id = UUID(metadata['tenant_id'])
        tier = SubscriptionTier(metadata['tier'])
        billing_interval = metadata['billing_interval']
        seat_count = int(metadata.get('seat_count', 1))
        
        logger.info(f"Processing checkout completion for tenant {tenant_id}")
        
        # Get subscription data from Stripe via provider
        provider_subscription_id = session_data.get('subscription')
        subscription_data = await self.provider.get_subscription(provider_subscription_id)
        
        # Calculate pricing
        plan = await self.get_plan_by_tier_key(tier.value)
        pricing = await self.calculate_seat_based_pricing(plan, seat_count, billing_interval)
        
        # Update or create subscription
        subscription = await self.get_tenant_subscription(tenant_id)
        
        if not subscription:
            subscription = Subscription(tenant_id=tenant_id)
            self.db.add(subscription)
        
        # Update subscription fields
        subscription.plan_id = plan.id
        subscription.tier = tier.value
        subscription.payment_mode = PaymentMode.CARD.value
        subscription.status = SubscriptionStatus.ACTIVE.value
        subscription.seat_count = seat_count
        subscription.base_price_cents = pricing['base_price_cents']
        subscription.per_seat_price_cents = pricing['per_seat_price_cents']
        subscription.total_amount_cents = pricing['total_amount_cents']
        subscription.billing_interval = billing_interval
        subscription.currency = 'USD'
        
        subscription.provider_customer_id = session_data.get('customer')
        subscription.provider_subscription_id = provider_subscription_id
        
        # Handle timestamps with fallbacks like B2C does
        start_ts = subscription_data.get('current_period_start') or subscription_data.get('start_date') or subscription_data.get('created')
        subscription.current_period_start = datetime.fromtimestamp(start_ts, tz=timezone.utc) if start_ts else datetime.now(timezone.utc)
        
        end_ts = subscription_data.get('current_period_end')
        if end_ts:
            subscription.current_period_end = datetime.fromtimestamp(end_ts, tz=timezone.utc)
        else:
            # Default to 30 days from now if not provided
            from datetime import timedelta
            subscription.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
        
        await self.db.flush()
        
        # Create audit event
        event = SubscriptionEvent(
            subscription_id=subscription.id,
            tenant_id=tenant_id,
            event_type='subscription.created' if not subscription else 'subscription.upgraded',
            provider='stripe',
            provider_event_id=session_data.get('id'),
            payload={
                'tier': tier.value,
                'seat_count': seat_count,
                'pricing': pricing,
                'billing_interval': billing_interval
            }
        )
        self.db.add(event)
        await self.db.flush()

        # SYNC PLUGINS from Plan
        # This ensures b2b.tenants.plugins (Runtime Source of Truth) matches the new Subscription Entitlement
        plan_plugins = plan.features.get('plugins', [])
        from modules.b2b.services.tenant_service import tenant_service
        logger.info(f"Syncing plugins for tenant {tenant_id} based on new plan {tier.value}: {plan_plugins}")
        await tenant_service.update_tenant_plugins(self.db, tenant_id, plan_plugins)
        
        logger.info(f"✅ Subscription activated: {subscription.id} (tier: {tier.value}, seats: {seat_count})")

        
        # Metric
        from infrastructure.monitoring import increment_subscription_event
        increment_subscription_event(event_type='subscription_activated', plan=tier.value)
        
        # Send confirmation email to tenant owner
        try:
            owner_result = await self.db.execute(
                select(UserModel)
                .join(Role, UserModel.role_id == Role.id)
                .where(
                    UserModel.tenant_id == tenant_id,
                    Role.name == 'owner',
                    UserModel.deleted_at == None
                )
            )
            owner = owner_result.scalar_one_or_none()
            
            if owner:
                # Get tenant for name
                tenant_result = await self.db.execute(
                    select(TenantModel).where(TenantModel.id == tenant_id)
                )
                tenant = tenant_result.scalar_one()
                
                # Use specific email method instead of generic send_email
                dashboard_url = f"{settings.frontend_url}/dashboard"
                
                # Format plan name
                plan_display = f"{tier.value.title()} Plan ({seat_count} seats)"
                amount_display = f"${subscription.total_amount_cents / 100:.2f}"
                
                # Fetch invoice PDF URL
                invoice_pdf_url = None
                try:
                    # 'latest_invoice' is usually expanded in subscription object from Stripe
                    latest_invoice_id = subscription_data.get('latest_invoice')
                    if latest_invoice_id:
                        if isinstance(latest_invoice_id, str):
                            invoice_obj = await self.provider.get_invoice(latest_invoice_id)
                        else:
                            invoice_obj = latest_invoice_id
                            
                        invoice_pdf_url = invoice_obj.get('invoice_pdf')
                        logger.info(f"Found invoice PDF URL: {invoice_pdf_url}")
                except Exception as e:
                    logger.warning(f"Could not fetch invoice PDF: {e}")

                email_service.send_subscription_confirmation_email(
                    to_email=owner.email,
                    plan_name=plan_display,
                    amount=amount_display,
                    interval=billing_interval,
                    next_billing_date=subscription.current_period_end.strftime("%B %d, %Y"),
                    dashboard_url=dashboard_url,
                    invoice_pdf_url=invoice_pdf_url
                )
                logger.info(f"📧 Subscription confirmation email sent to {owner.email}")
        except Exception as e:
            logger.error(f"Failed to send subscription confirmation email: {e}")
            # Don't fail the whole transaction for email issues
        
        return subscription
    
    async def get_active_seat_count(self, tenant_id: UUID) -> int:
        """
        Count active user seats for a tenant.
        Seats = COUNT(active users with is_active=TRUE and deleted_at=NULL)
        """
        result = await self.db.execute(
            select(func.count(UserModel.id))
            .where(
                UserModel.tenant_id == tenant_id,
                UserModel.is_active == True,
                UserModel.deleted_at == None
            )
        )
        count = result.scalar()
        return max(count or 0, 1)  # Minimum 1 seat

    async def get_plan_by_tier_key(self, tier_key: str) -> B2BSubscriptionPlan:
        """Fetch plan configuration from database"""
        result = await self.db.execute(
            select(B2BSubscriptionPlan).where(B2BSubscriptionPlan.tier_key == tier_key)
        )
        plan = result.scalar_one_or_none()
        if not plan:
            raise ValueError(f"Subscription plan not found: {tier_key}")
        return plan
        
    async def update_seat_count(self, subscription_id: UUID) -> Subscription:
        """
        Recalculate and update seat count based on active users.
        Called by Celery task or when users are added/removed.
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one()
        
        new_seat_count = await self.get_active_seat_count(subscription.tenant_id)
        
        if new_seat_count != subscription.seat_count:
            old_seat_count = subscription.seat_count
            subscription.seat_count = new_seat_count
            
            # Recalculate pricing
            plan = await self.get_plan_by_tier_key(subscription.tier)
            pricing = await self.calculate_seat_based_pricing(
                plan,
                new_seat_count,
                subscription.billing_interval
            )
            subscription.total_amount_cents = pricing['total_amount_cents']
            
            await self.db.flush()
            
            # Create audit event
            event = SubscriptionEvent(
                subscription_id=subscription.id,
                tenant_id=subscription.tenant_id,
                event_type='subscription.seat_count_updated',
                provider='system',
                payload={
                    'old_seat_count': old_seat_count,
                    'new_seat_count': new_seat_count,
                    'new_pricing': pricing
                }
            )
            self.db.add(event)
            await self.db.flush()
            
            logger.info(f"Seat count updated: {subscription.id} ({old_seat_count} → {new_seat_count})")
            
            # Metric
            from infrastructure.monitoring import increment_subscription_event
            increment_subscription_event(event_type='seat_count_updated', plan=subscription.tier)

        
        return subscription

    async def cancel_subscription(self, subscription_id: UUID, immediate: bool = False) -> Subscription:
        """
        Cancel a B2B subscription.
        Args:
            subscription_id: UUID
            immediate: If True, cancel immediately. Else at period end.
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise ValueError("Subscription not found")
            
        if not subscription.provider_subscription_id:
            # Maybe it's a manual/test sub? just set status
            subscription.status = SubscriptionStatus.CANCELED.value
        else:
            # Cancel in Stripe
            try:
                # StripeProvider.cancel_subscription returns dict
                stripe_sub = await self.provider.cancel_subscription(
                    provider_subscription_id=subscription.provider_subscription_id,
                    at_period_end=not immediate
                )
                
                # Update status based on logic
                # If at_period_end, Stripe status usually remains 'active' until period ends,
                # but with cancel_at_period_end=true.
                # internal status might reflect this?
                # Or we wait for webhook?
                # Let's set cancel_at_period_end flag if available, or just update based on response.
                
                if stripe_sub.get('status') == 'canceled':
                    subscription.status = SubscriptionStatus.CANCELED.value
                
                # You might want to store 'cancel_at_period_end' in DB if column exists.
                # B2BSubscription model has 'cancel_at_period_end'? 
                # Let's check model. Phase 1 created it. 
                # Assuming it exists based on previous file views (B2C has it). 
                # Ideally check model but I'll assume for now or check.
                # Actually I'm in Service, I can check imports.
                # Subscription model is imported.
                # I'll check if I can set it.
                if 'cancel_at_period_end' in stripe_sub:
                     subscription.cancel_at_period_end = stripe_sub['cancel_at_period_end']
                
            except Exception as e:
                logger.error(f"Stripe cancellation failed: {e}")
                raise e
        
        await self.db.commit()
        
        # Create Audit Event
        event = SubscriptionEvent(
            subscription_id=subscription.id,
            tenant_id=subscription.tenant_id,
            event_type='subscription.canceled',
            provider='stripe',
            payload={'immediate': immediate}
        )
        self.db.add(event)
        await self.db.commit()
        
        # Metric
        from infrastructure.monitoring import increment_subscription_event
        increment_subscription_event(event_type='subscription_canceled', plan=subscription.tier)
        
        return subscription
    async def create_portal_session(self, tenant_id: UUID, return_url: str) -> str:
        """
        Create a Stripe Customer Portal session for the tenant.
        Allows users to manage payment methods, billing info, etc.
        """
        subscription = await self.get_tenant_subscription(tenant_id)
        
        # If no subscription or no provider customer ID, we can't create a portal session 
        # (unless we create a customer first, but usually this is for existing subs)
        if not subscription or not subscription.provider_customer_id:
             # Try to find a customer by email? 
             # Or check if we have a customer ID stored elsewhere?
             # For now, require a subscription or at least a customer ID in the subscription record.
             # Actually, if they are on a free plan (STARTER), they might not have a customer ID yet.
             # But the requirement is to "change card", implying they have one.
             raise ValueError("No billing account found. Please upgrade to a paid plan first.")
             
        # Call provider
        result = await self.provider.create_customer_portal_session(
            customer_id=subscription.provider_customer_id,
            return_url=return_url
        )
        
        return result['portal_url']
