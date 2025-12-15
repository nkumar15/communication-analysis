"""
Subscription Service

Business logic for subscription management, checkout, and billing.
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from core.payment import PaymentProviderFactory
from core.config import settings
from services.b2c.models.subscription import Subscription, Invoice, PaymentMethod
from services.b2c.models.user import B2CUser
from services.b2c.models.workspace import Workspace

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Service for managing B2C subscriptions and billing.
    """
    
    def __init__(self, db: Session):
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
    
    async def get_or_create_customer(self, user: B2CUser) -> str:
        """
        Get existing Stripe customer ID or create a new customer.
        
        Args:
            user: B2C user object
            
        Returns:
            Provider customer ID
        """
        # Check if user already has a subscription with customer ID
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()
        
        if subscription and subscription.provider_customer_id:
            return subscription.provider_customer_id
        
        # Create new customer
        logger.info(f"Creating new Stripe customer for user {user.id}")
        result = await self.provider.create_customer(
            user_id=str(user.id),
            email=user.email,
            name=user.display_name,
            metadata={'user_id': str(user.id)}
        )
        
        provider_customer_id = result['provider_customer_id']
        
        # Update subscription with customer ID if exists
        if subscription:
            subscription.provider_customer_id = provider_customer_id
            self.db.commit()
        
        return provider_customer_id
    
    async def create_checkout_session(
        self,
        user: B2CUser,
        workspace: Workspace,
        tier: str,
        billing_interval: str = 'monthly',
        coupon_code: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription purchase.
        
        Args:
            user: B2C user
            workspace: Workspace to subscribe
            tier: 'premium' or 'ultimate'
            billing_interval: 'monthly' or 'yearly'
            coupon_code: Optional coupon code for discount
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment cancelled
            
        Returns:
            {
                'checkout_session_id': str,
                'checkout_url': str
            }
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
        logger.info(f"Creating checkout session for user {user.id}, tier {tier}")
        
        metadata = {
            'user_id': str(user.id),
            'workspace_id': str(workspace.id),
            'tier': tier,
            'billing_interval': billing_interval
        }
        
        # Validate and apply coupon if provided
        if coupon_code:
            from services.b2c.services.coupon_service import CouponService
            coupon_service = CouponService(self.db)
            
            try:
                coupon = coupon_service.validate_coupon(
                    code=coupon_code,
                    user=user,
                    tier=tier
                )
                metadata['coupon_code'] = coupon.code
                logger.info(f"Coupon validated: {coupon.code}")
            except Exception as e:
                logger.warning(f"Coupon validation failed: {str(e)}")
                # Don't fail checkout if coupon is invalid, just proceed without it
        
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
        
        Args:
            session_data: Stripe checkout.session.completed event data
            
        Returns:
            Updated Subscription object
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
        subscription = self.db.query(Subscription).filter(
            Subscription.workspace_id == workspace_id
        ).first()
        
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
        subscription.current_period_start = datetime.fromtimestamp(subscription_data['current_period_start'])
        subscription.current_period_end = datetime.fromtimestamp(subscription_data['current_period_end'])
        
        # Calculate amount in cents
        subscription.amount_cents = subscription_data['items']['data'][0]['price']['unit_amount']
        subscription.currency = subscription_data['items']['data'][0]['price']['currency'].upper()
        
        self.db.commit()
        self.db.refresh(subscription)
        
        logger.info(f"Subscription activated: {subscription.id} (tier: {tier})")
        
        return subscription
    
    async def handle_subscription_updated(self, subscription_data: Dict[str, Any]) -> Subscription:
        """
        Sync subscription updates from provider (called from webhook).
        
        Args:
            subscription_data: Stripe subscription.updated event data
            
        Returns:
            Updated Subscription object
        """
        provider_subscription_id = subscription_data['id']
        
        subscription = self.db.query(Subscription).filter(
            Subscription.provider_subscription_id == provider_subscription_id
        ).first()
        
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
        
        self.db.commit()
        self.db.refresh(subscription)
        
        logger.info(f"Subscription updated: {subscription.id} (status: {subscription.status})")
        
        return subscription
    
    async def cancel_subscription(self, workspace: Workspace, immediate: bool = False) -> Subscription:
        """
        Cancel a subscription.
        
        Args:
            workspace: Workspace with subscription
            immediate: If True, cancel immediately. If False, cancel at period end.
            
        Returns:
            Updated Subscription object
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.workspace_id == workspace.id
        ).first()
        
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
        
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    async def get_subscription(self, workspace: Workspace) -> Optional[Subscription]:
        """
        Get subscription for a workspace.
        
        Args:
            workspace: Workspace
            
        Returns:
            Subscription or None
        """
        return self.db.query(Subscription).filter(
            Subscription.workspace_id == workspace.id
        ).first()
    
    async def create_customer_portal_session(self, user: B2CUser, return_url: str) -> str:
        """
        Create Stripe Customer Portal session for self-service.
        
        Args:
            user: B2C user
            return_url: URL to return to after portal session
            
        Returns:
            Portal URL
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
        
        Args:
            invoice_data: Stripe invoice object
            
        Returns:
            Invoice object
        """
        provider_invoice_id = invoice_data['id']
        
        # Find subscription
        subscription = None
        if invoice_data.get('subscription'):
            subscription = self.db.query(Subscription).filter(
                Subscription.provider_subscription_id == invoice_data['subscription']
            ).first()
        
        # Check if invoice exists
        invoice = self.db.query(Invoice).filter(
            Invoice.provider_invoice_id == provider_invoice_id
        ).first()
        
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
        
        self.db.commit()
        self.db.refresh(invoice)
        
        return invoice
