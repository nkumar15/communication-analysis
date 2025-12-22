"""
Async Subscription Service

Business logic for subscription management, checkout, and billing.
Uses async SQLAlchemy patterns for compatibility with AsyncSession.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
import logging

from infrastructure.payment import PaymentProviderFactory
from core.config import settings
from services.b2c.models.subscription import Subscription, Invoice, PaymentMethod
from services.b2c.models.subscription_plan import SubscriptionPlan
from services.b2c.models.user import B2CUser
from services.b2c.models.workspace import Workspace

logger = logging.getLogger(__name__)


def get_user_id(user: Union[B2CUser, Dict[str, Any]]) -> Any:
    """Extract user ID from either a B2CUser object or a dict."""
    if isinstance(user, dict):
        return user.get('id')
    return user.id


def get_user_email(user: Union[B2CUser, Dict[str, Any]]) -> str:
    """Extract user email from either a B2CUser object or a dict."""
    if isinstance(user, dict):
        return user.get('email', '')
    return user.email or ''


def get_user_display_name(user: Union[B2CUser, Dict[str, Any]]) -> str:
    """Extract user display name from either a B2CUser object or a dict."""
    if isinstance(user, dict):
        return user.get('display_name', '')
    return user.display_name or ''


class SubscriptionService:
    """
    Async service for managing B2C subscriptions and billing.
    All database operations use async SQLAlchemy patterns.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # self.provider removed in favor of dynamic instantiation
        
    def _get_provider_instance(self, provider_name: str):
        """Helper to create provider instance with correct config"""
        config = {}
        if provider_name == 'stripe':
            config = {
                'secret_key': settings.stripe_secret_key,
                'webhook_secret': settings.stripe_webhook_secret,
            }
        elif provider_name == 'razorpay':
            config = {
                'key_id': settings.razorpay_key_id,
                'key_secret': settings.razorpay_key_secret,
            }
        elif provider_name == 'xendit':
            config = {
                'secret_key': settings.xendit_secret_key,
            }
            
        return PaymentProviderFactory.create(provider_name, config)
        
        
        # Price mapping (deprecated in favor of database-driven plans)
        # self.price_map = {}
    
    async def get_or_create_customer(self, user, provider_name: str = 'stripe') -> str:
        """
        Get existing customer ID or create a new customer for the specific provider.
        """
        user_id = get_user_id(user)
        
        # Check if user already has a subscription with customer ID for this provider
        # Note: We might want to store customer IDs in a separate table or JSONB if a user uses multiple providers
        # For now, we check the subscription table. 
        # CAUTION: If user switches providers, this logic relies on them having an active subscription 
        # OR we need to accept that one user might have different customer IDs for different providers.
        # But `Subscription` is unique per workspace. 
        
        # Helper: Try to find a subscription with matching provider
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id, 
                Subscription.provider == provider_name
            )
        )
        subscription = result.scalar_one_or_none()
        
        if subscription and subscription.provider_customer_id:
            return subscription.provider_customer_id
        
        # Create new customer
        user_email = get_user_email(user)
        user_display_name = get_user_display_name(user)
        
        logger.info(f"Creating new {provider_name} customer for user {user_id}")
        provider = self._get_provider_instance(provider_name)
        
        result = await provider.create_customer(
            user_id=str(user_id),
            email=user_email,
            name=user_display_name,
            metadata={'user_id': str(user_id)}
        )
        
        provider_customer_id = result['provider_customer_id']
        
        # We don't necessarily have a subscription to update yet. 
        # Typically this is called before checkout.
        
        return provider_customer_id
    
    async def create_checkout_session(
        self,
        user,
        workspace: Workspace,
        tier: str,
        billing_interval: str = 'monthly',
        coupon_code: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription purchase.
        """
        if billing_interval not in ['monthly', 'yearly']:
            raise ValueError(f"Invalid billing interval: {billing_interval}")
        
        # 1. Fetch Active Subscription Plan from DB
        # Look for a plan with matching tier_key that is currently effective
        stmt = select(SubscriptionPlan).where(
            SubscriptionPlan.tier_key == tier,
            SubscriptionPlan.effective_from <= datetime.now(timezone.utc),
            SubscriptionPlan.archived_at.is_(None)
        ).order_by(SubscriptionPlan.effective_from.desc()).limit(1)
        
        result = await self.db.execute(stmt)
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise ValueError(f"Plan not found or not active: {tier}")
            
        provider_config = plan.provider_config or {}
        
        # Determine Provider
        provider_name = 'stripe' # default
        if 'razorpay' in provider_config:
            provider_name = 'razorpay'
        elif 'xendit' in provider_config:
            provider_name = 'xendit'
        elif 'stripe' in provider_config:
            provider_name = 'stripe'
            
        provider_data = provider_config.get(provider_name, {})
        
        # Extract Price/Plan ID
        price_id = None
        if provider_name == 'stripe':
            price_key = f"{billing_interval}_price_id"
            price_id = provider_data.get(price_key)
        elif provider_name in ['razorpay', 'xendit']:
            # Assuming flat structure or similar for others for now
            price_id = provider_data.get('plan_id') or provider_data.get(f"{provider_name}_plan_id")

        if not price_id:
            raise ValueError(f"Price/Plan ID not configured for {tier} ({provider_name})")
        
        # Get or create customer for this provider
        customer_id = await self.get_or_create_customer(user, provider_name)
        
        # Default URLs
        if not success_url:
            success_url = f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        if not cancel_url:
            cancel_url = f"{settings.frontend_url}/pricing"
        
        # Create checkout session
        user_id = get_user_id(user)
        logger.info(f"Creating {provider_name} checkout session for user {user_id}, plan {plan.name}")
        
        metadata = {
            'user_id': str(user_id),
            'workspace_id': str(workspace.id),
            'plan_id': str(plan.id), 
            'tier': tier,
            'billing_interval': billing_interval,
            'provider': provider_name 
        }
        
        # Validate and apply coupon if provided
        if coupon_code:
            from services.b2c.services.coupon_service import CouponService
            coupon_service = CouponService(self.db)
            try:
                coupon = await coupon_service.validate_coupon(
                    code=coupon_code,
                    user=user,
                    tier=tier
                )
                metadata['coupon_code'] = coupon.code
                logger.info(f"Coupon validated: {coupon.code}")
            except Exception as e:
                logger.warning(f"Coupon validation failed: {str(e)}")
        
        # Instantiate Provider
        provider = self._get_provider_instance(provider_name)

        result = await provider.create_checkout_session(
            customer_id=customer_id,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata
        )
        
        return {
            'checkout_session_id': result['checkout_session_id'],
            'checkout_url': result['checkout_url']
        }
    
    async def handle_checkout_completed(self, session_data: Dict[str, Any], provider_name: str = 'stripe') -> Subscription:
        """
        Process successful checkout (called from webhook).
        """
        metadata = session_data.get('metadata', {})
        user_id = metadata.get('user_id')
        workspace_id = metadata.get('workspace_id')
        plan_id = metadata.get('plan_id')
        billing_interval = metadata.get('billing_interval')
        tier = metadata.get('tier') 
        
        logger.info(f"Processing {provider_name} checkout completion for workspace {workspace_id}")
        
        # Get subscription info from Provider
        provider = self._get_provider_instance(provider_name)
        provider_subscription_id = session_data.get('subscription')
        subscription_data = await provider.get_subscription(provider_subscription_id)
        
        # Update or create subscription
        result = await self.db.execute(
            select(Subscription).where(Subscription.workspace_id == workspace_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            subscription = Subscription(
                workspace_id=workspace_id,
                user_id=user_id,
                provider=provider_name
            )
            self.db.add(subscription)
        
        # Update provider if needed (e.g. reactivation with different provider)
        subscription.provider = provider_name
        
        # Update subscription fields
        subscription.provider_customer_id = session_data.get('customer')
        subscription.provider_subscription_id = provider_subscription_id
        if plan_id:
            subscription.plan_id = plan_id
        subscription.billing_interval = billing_interval
        subscription.status = subscription_data.get('status', 'active')
        
        # Handle start date
        start_ts = subscription_data.get('current_period_start') or subscription_data.get('start_date') or subscription_data.get('created')
        subscription.current_period_start = datetime.fromtimestamp(start_ts, tz=timezone.utc) if start_ts else datetime.now(timezone.utc)
        
        # Handle end date
        end_ts = subscription_data.get('current_period_end')
        if end_ts:
            subscription.current_period_end = datetime.fromtimestamp(end_ts, tz=timezone.utc)
        else:
            # Fallback: calculate based on billing interval or default to 30 days
            import time
            subscription.current_period_end = datetime.fromtimestamp(time.time() + 30*24*60*60, tz=timezone.utc)
         
        # Make sure cancel_at_period_end is boolean
        subscription.cancel_at_period_end = bool(subscription_data.get('cancel_at_period_end'))
        
        
        # Calculate amount in cents
        # Handle cases where items might be empty or structured differently
        try:
            items_data = subscription_data.get('items', {}).get('data', [])
            if items_data:
                price_obj = items_data[0].get('price', {})
                subscription.amount_cents = price_obj.get('unit_amount', 0)
                subscription.currency = price_obj.get('currency', 'usd').upper()
            else:
                subscription.amount_cents = 0
                subscription.amount_cents = 0
                subscription.currency = 'USD'
        except Exception as e:
            logger.warning(f"Could not extract price from subscription items: {e}")
            subscription.amount_cents = 0
            subscription.currency = 'USD'
        
        # Sync Workspace subscription tier
        if tier:
            result = await self.db.execute(select(Workspace).where(Workspace.id == workspace_id))
            workspace_obj = result.scalar_one_or_none()
            if workspace_obj:
                workspace_obj.subscription_tier = tier
                
        await self.db.flush()
        
        logger.info(f"Subscription activated: {subscription.id} (plan: {plan_id})")
        
        # Send confirmation email
        try:
            from workers.b2b_worker.email_tasks import send_subscription_confirmation_email
            
            # Get user email from session customer details or fallback
            customer_details = session_data.get('customer_details') or {}
            to_email = customer_details.get('email')
            
            if not to_email and user_id:
                # Fallback to DB query if Stripe didn't provide email
                # We can reuse the helper but we need the object. 
                # Let's just query B2CUser.
                from services.b2c.models.user import B2CUser
                result = await self.db.execute(select(B2CUser).where(B2CUser.id == user_id))
                user_obj = result.scalar_one_or_none()
                if user_obj:
                    to_email = user_obj.email

            if to_email:
                plan_display = f"{tier.title()} {billing_interval.title()}" if tier else "Subscription"
                
                # Format amount
                currency_symbol = "$" if subscription.currency in ['USD', 'SGD', 'AUD', 'CAD'] else subscription.currency + " "
                amount_formatted = f"{currency_symbol}{subscription.amount_cents / 100:.2f}"
                
                next_date = subscription.current_period_end.strftime('%B %d, %Y')
                dashboard_url = f"{settings.frontend_url}/dashboard"
                
                # Fetch invoice PDF URL
                invoice_pdf_url = None
                try:
                    latest_invoice_id = subscription_data.get('latest_invoice')
                    if latest_invoice_id:
                        # If it's a string, fetch it. If it's an object (dict), use it.
                        if isinstance(latest_invoice_id, str):
                            invoice = await provider.get_invoice(latest_invoice_id)
                        else:
                            invoice = latest_invoice_id
                            
                        invoice_pdf_url = invoice.get('invoice_pdf')
                        logger.info(f"Found invoice PDF URL: {invoice_pdf_url}")
                except Exception as e:
                    logger.warning(f"Could not fetch invoice PDF: {e}")
                
                send_subscription_confirmation_email.delay(
                    to_email=to_email,
                    plan_name=plan_display,
                    amount=amount_formatted,
                    interval=billing_interval,
                    next_billing_date=next_date,
                    dashboard_url=dashboard_url,
                    invoice_pdf_url=invoice_pdf_url
                )
                logger.info(f"Triggered confirmation email to {to_email}")
            else:
                logger.warning("Could not determine email for subscription confirmation")
                
        except Exception as e:
            logger.error(f"Failed to trigger subscription email: {e}")
        
        return subscription
    
    async def handle_subscription_updated(self, subscription_data: Dict[str, Any]) -> Optional[Subscription]:
        """
        Sync subscription updates from provider (called from webhook).
        """
        provider_subscription_id = subscription_data['id']
        
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.provider_subscription_id == provider_subscription_id
            )
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            logger.warning(f"Subscription not found: {provider_subscription_id}")
            return None
        
        # Update status and period
        subscription.status = subscription_data.get('status')
        subscription.current_period_start = datetime.fromtimestamp(subscription_data['current_period_start'], tz=timezone.utc)
        subscription.current_period_end = datetime.fromtimestamp(subscription_data['current_period_end'], tz=timezone.utc)
        subscription.cancel_at_period_end = subscription_data.get('cancel_at_period_end', False)
        
        if subscription_data.get('canceled_at'):
            subscription.canceled_at = datetime.fromtimestamp(subscription_data['canceled_at'], tz=timezone.utc)

        # Fix: Sync Plan/Tier from Price ID
        # When user upgrades/downgrades via Portal, `items` array has the new Price ID.
        try:
            items_data = subscription_data.get('items', {}).get('data', [])
            if items_data:
                price_obj = items_data[0].get('price', {})
                price_id = price_obj.get('id')
                
                if price_id:
                    # Find plan with this price_id in provider_config
                    # Note: We need to search inside the JSONB. 
                    # Assuming Stripe structure: provider_config = {"stripe": {"monthly_price_id": "...", "yearly_price_id": "..."}}
                    # We can use SQL JSON operators or just filtered search.
                    # Since plans table is small, searching is cheap.
                    # OR match explicitly.
                    from sqlalchemy import or_
                    
                    # Safer to scan all active plans and match python side if JSON usage is complex for cross-db compat or just complex query
                    # But proper way is JSON path.
                    # For now let's query all active plans and find match.
                    plans_result = await self.db.execute(select(SubscriptionPlan))
                    all_plans = plans_result.scalars().all()
                    
                    found_plan = None
                    new_billing_interval = 'monthly'
                    
                    for plan in all_plans:
                         config = plan.provider_config or {}
                         stripe = config.get('stripe', {})
                         if stripe.get('monthly_price_id') == price_id:
                             found_plan = plan
                             new_billing_interval = 'monthly'
                             break
                         if stripe.get('yearly_price_id') == price_id:
                             found_plan = plan
                             new_billing_interval = 'yearly'
                             break
                    
                    if found_plan:
                        subscription.plan_id = found_plan.id
                        subscription.billing_interval = new_billing_interval
                        
                        # Sync Workspace Priority
                        if subscription.workspace_id:
                            ws_result = await self.db.execute(select(Workspace).where(Workspace.id == subscription.workspace_id))
                            workspace_obj = ws_result.scalar_one_or_none()
                            if workspace_obj:
                                workspace_obj.subscription_tier = found_plan.tier_key
                                
                        logger.info(f"Syncing subscription plan to {found_plan.tier_key} ({found_plan.id}) from price {price_id}")
                    else:
                        logger.warning(f"No plan found for price ID {price_id}")

        except Exception as e:
            logger.error(f"Failed to sync plan from price ID: {e}")
        
        await self.db.flush()
        
        logger.info(f"Subscription updated: {subscription.id} (status: {subscription.status})")
        
        return subscription
    
    async def cancel_subscription(
        self, 
        workspace: Workspace, 
        immediate: bool = False
    ) -> Subscription:
        """
        Cancel a subscription.
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.workspace_id == workspace.id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription or not subscription.provider_subscription_id:
            raise ValueError("No active subscription found")
        
        logger.info(f"Canceling subscription {subscription.id} (immediate: {immediate})")
        
        # Instantiate provider
        provider = self._get_provider_instance(subscription.provider)
        
        # Cancel with provider
        result = await provider.cancel_subscription(
            provider_subscription_id=subscription.provider_subscription_id,
            at_period_end=not immediate
        )
        
        # Update local record
        subscription.status = result['status']
        subscription.cancel_at_period_end = result.get('cancel_at_period_end', False)
        if result.get('canceled_at'):
            subscription.canceled_at = result['canceled_at']
        
        await self.db.flush()
        
        return subscription
    
    async def get_subscription(self, workspace: Workspace) -> Optional[Subscription]:
        """
        Get subscription for a workspace.
        """
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.workspace_id == workspace.id)
            .options(selectinload(Subscription.plan))
        )
        return result.scalar_one_or_none()
    
    async def create_customer_portal_session(
        self, 
        user, 
        return_url: str
    ) -> str:
        """
        Create Customer Portal session for self-service.
        """
        # Determine provider: Check if user has an active subscription
        user_id = get_user_id(user)
        provider_name = 'stripe' # default
        
        # We need to find if there is an active subscription for this user to know the provider
        # Assuming user has only one active subscription for now (B2C model)
        # Or we check the B2CUser if we store provider there.
        # Let's check matching subscription.
        stmt = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status.in_(['active', 'trialing', 'past_due'])
        ).limit(1)
        result = await self.db.execute(stmt)
        sub = result.scalar_one_or_none()
        
        if sub:
            provider_name = sub.provider
        
        customer_id = await self.get_or_create_customer(user, provider_name)
        
        provider = self._get_provider_instance(provider_name)
        
        result = await provider.create_customer_portal_session(
            customer_id=customer_id,
            return_url=return_url
        )
        
        return result['portal_url']
    
    async def sync_invoice(self, invoice_data: Dict[str, Any]) -> Invoice:
        """
        Sync invoice from provider to database.
        """
        provider_invoice_id = invoice_data['id']
        
        # Find subscription
        subscription = None
        if invoice_data.get('subscription'):
            result = await self.db.execute(
                select(Subscription).where(
                    Subscription.provider_subscription_id == invoice_data['subscription']
                )
            )
            subscription = result.scalar_one_or_none()
        
        # Check if invoice exists
        result = await self.db.execute(
            select(Invoice).where(Invoice.provider_invoice_id == provider_invoice_id)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            invoice = Invoice(provider_invoice_id=provider_invoice_id)
            self.db.add(invoice)
        
        # Update fields
        invoice.subscription_id = subscription.id if subscription else None
        invoice.user_id = subscription.user_id if subscription else None
        invoice.amount_due = invoice_data.get('amount_due', 0)
        invoice.amount_paid = invoice_data.get('amount_paid', 0)
        invoice.currency = invoice_data.get('currency', 'usd').upper()
        invoice.status = invoice_data.get('status')
        invoice.invoice_pdf_url = invoice_data.get('invoice_pdf')
        invoice.hosted_invoice_url = invoice_data.get('hosted_invoice_url')
        
        if invoice_data.get('created'):
            invoice.invoice_date = datetime.fromtimestamp(invoice_data['created'], tz=timezone.utc)
        if invoice_data.get('status_transitions', {}).get('paid_at'):
            invoice.paid_at = datetime.fromtimestamp(invoice_data['status_transitions']['paid_at'], tz=timezone.utc)
            
        # Extract billing period
        if invoice_data.get('period_start'):
            invoice.billing_period_start = datetime.fromtimestamp(invoice_data['period_start'], tz=timezone.utc)
        if invoice_data.get('period_end'):
            invoice.billing_period_end = datetime.fromtimestamp(invoice_data['period_end'], tz=timezone.utc)
        
        # Fallback to lines if top-level period not available/accurate (typical in some Stripe setups)
        # But generally for subscription invoices, period_start/end on invoice object are correct.
        if not invoice.billing_period_start and invoice_data.get('lines', {}).get('data'):
             # Try to get from first line item
             first_line = invoice_data['lines']['data'][0]
             if first_line.get('period'):
                 invoice.billing_period_start = datetime.fromtimestamp(first_line['period']['start'], tz=timezone.utc)
                 invoice.billing_period_end = datetime.fromtimestamp(first_line['period']['end'], tz=timezone.utc)
        
        await self.db.flush()
        
        return invoice
