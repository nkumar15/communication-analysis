"""
Async Subscription Service

Business logic for subscription management, checkout, and billing.
Uses async SQLAlchemy patterns for compatibility with AsyncSession.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any, Union
from datetime import datetime
import logging

from core.payment import PaymentProviderFactory
from core.config import settings
from services.b2c.models.subscription import Subscription, Invoice, PaymentMethod
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
        
        # Initialize payment provider
        self.provider = PaymentProviderFactory.create(
            settings.payment_provider,
            config={
                'secret_key': settings.stripe_secret_key,
                'webhook_secret': settings.stripe_webhook_secret,
            }
        )
        
        # Price mapping
        self.price_map = {
            ('premium', 'monthly'): settings.stripe_price_premium_monthly,
            ('premium', 'yearly'): settings.stripe_price_premium_yearly,
            ('ultimate', 'monthly'): settings.stripe_price_ultimate_monthly,
            ('ultimate', 'yearly'): settings.stripe_price_ultimate_yearly,
        }
    
    async def get_or_create_customer(self, user) -> str:
        """
        Get existing Stripe customer ID or create a new customer.
        """
        user_id = get_user_id(user)
        
        # Check if user already has a subscription with customer ID
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()
        
        if subscription and subscription.provider_customer_id:
            return subscription.provider_customer_id
        
        # Create new customer
        user_email = get_user_email(user)
        user_display_name = get_user_display_name(user)
        
        logger.info(f"Creating new Stripe customer for user {user_id}")
        result = await self.provider.create_customer(
            user_id=str(user_id),
            email=user_email,
            name=user_display_name,
            metadata={'user_id': str(user_id)}
        )
        
        provider_customer_id = result['provider_customer_id']
        
        # Update subscription with customer ID if exists
        if subscription:
            subscription.provider_customer_id = provider_customer_id
            await self.db.flush()
        
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
        if tier not in ['premium', 'ultimate']:
            raise ValueError(f"Invalid tier: {tier}")
        
        if billing_interval not in ['monthly', 'yearly']:
            raise ValueError(f"Invalid billing interval: {billing_interval}")
        
        # Get or create customer
        customer_id = await self.get_or_create_customer(user)
        
        # Get price ID
        price_id = self.price_map.get((tier, billing_interval))
        if not price_id:
            raise ValueError(f"Price not configured for {tier} {billing_interval}")
        
        # Default URLs
        if not success_url:
            success_url = f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        if not cancel_url:
            cancel_url = f"{settings.frontend_url}/pricing"
        
        # Create checkout session
        user_id = get_user_id(user)
        logger.info(f"Creating checkout session for user {user_id}, tier {tier}")
        
        # DEBUG: Print exact values being used
        print(f"DEBUG: Checkout Request - Tier: {tier}, Interval: {billing_interval}")
        print(f"DEBUG: Mapped Price ID: {price_id}")
        print(f"DEBUG: Configured keys:")
        print(f"  PREMIUM_MONTHLY: {settings.stripe_price_premium_monthly}")
        print(f"  PREMIUM_YEARLY: {settings.stripe_price_premium_yearly}")
        print(f"  ULTIMATE_MONTHLY: {settings.stripe_price_ultimate_monthly}")
        print(f"  ULTIMATE_YEARLY: {settings.stripe_price_ultimate_yearly}")
        
        metadata = {
            'user_id': str(user_id),
            'workspace_id': str(workspace.id),
            'tier': tier,
            'billing_interval': billing_interval
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
        
        result = await self.provider.create_checkout_session(
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
    
    async def handle_checkout_completed(self, session_data: Dict[str, Any]) -> Subscription:
        """
        Process successful checkout (called from webhook).
        """
        metadata = session_data.get('metadata', {})
        user_id = metadata.get('user_id')
        workspace_id = metadata.get('workspace_id')
        tier = metadata.get('tier')
        billing_interval = metadata.get('billing_interval')
        
        logger.info(f"Processing checkout completion for workspace {workspace_id}")
        
        # Get subscription info from Stripe
        provider_subscription_id = session_data.get('subscription')
        subscription_data = await self.provider.get_subscription(provider_subscription_id)
        
        # Update or create subscription
        result = await self.db.execute(
            select(Subscription).where(Subscription.workspace_id == workspace_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            subscription = Subscription(
                workspace_id=workspace_id,
                user_id=user_id
            )
            self.db.add(subscription)
        
        # Update subscription fields
        subscription.provider_customer_id = session_data.get('customer')
        subscription.provider_subscription_id = provider_subscription_id
        subscription.tier = tier
        subscription.billing_interval = billing_interval
        subscription.status = subscription_data.get('status', 'active')
        
        # Handle start date
        start_ts = subscription_data.get('current_period_start') or subscription_data.get('start_date') or subscription_data.get('created')
        subscription.current_period_start = datetime.fromtimestamp(start_ts) if start_ts else datetime.now()
        
        # Handle end date
        end_ts = subscription_data.get('current_period_end')
        if end_ts:
            subscription.current_period_end = datetime.fromtimestamp(end_ts)
        else:
            # Fallback: calculate based on billing interval or default to 30 days
            import time
            subscription.current_period_end = datetime.fromtimestamp(time.time() + 30*24*60*60)
         
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
                subscription.currency = 'USD'
        except Exception as e:
            logger.warning(f"Could not extract price from subscription items: {e}")
            subscription.amount_cents = 0
            subscription.currency = 'USD'
        
        await self.db.flush()
        
        logger.info(f"Subscription activated: {subscription.id} (tier: {tier})")
        
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
        subscription.current_period_start = datetime.fromtimestamp(subscription_data['current_period_start'])
        subscription.current_period_end = datetime.fromtimestamp(subscription_data['current_period_end'])
        subscription.cancel_at_period_end = subscription_data.get('cancel_at_period_end', False)
        
        if subscription_data.get('canceled_at'):
            subscription.canceled_at = datetime.fromtimestamp(subscription_data['canceled_at'])
        
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
        
        # Cancel with provider
        result = await self.provider.cancel_subscription(
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
            select(Subscription).where(Subscription.workspace_id == workspace.id)
        )
        return result.scalar_one_or_none()
    
    async def create_customer_portal_session(
        self, 
        user, 
        return_url: str
    ) -> str:
        """
        Create Stripe Customer Portal session for self-service.
        """
        customer_id = await self.get_or_create_customer(user)
        
        result = await self.provider.create_customer_portal_session(
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
            invoice.invoice_date = datetime.fromtimestamp(invoice_data['created'])
        if invoice_data.get('status_transitions', {}).get('paid_at'):
            invoice.paid_at = datetime.fromtimestamp(invoice_data['status_transitions']['paid_at'])
        
        await self.db.flush()
        
        return invoice
