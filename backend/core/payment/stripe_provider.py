"""
Stripe Payment Provider Implementation

This module implements the PaymentProvider interface for Stripe.
"""
import stripe
from typing import Dict, Any, Optional
from datetime import datetime
from .provider import PaymentProvider


class StripeProvider(PaymentProvider):
    """
    Stripe implementation of the PaymentProvider interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Stripe provider.
        
        Args:
            config: Must contain:
                - secret_key: Stripe secret key
                - webhook_secret: Stripe webhook signing secret
        """
        super().__init__(config)
        stripe.api_key = config['secret_key']
        self.webhook_secret = config['webhook_secret']
    
    async def create_customer(
        self,
        user_id: str,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a Stripe customer."""
        customer_metadata = metadata or {}
        customer_metadata['internal_user_id'] = user_id
        
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata=customer_metadata
        )
        
        return {
            'provider_customer_id': customer.id,
            'email': customer.email,
            'created_at': datetime.fromtimestamp(customer.created)
        }
    
    async def get_customer(self, provider_customer_id: str) -> Dict[str, Any]:
        """Retrieve Stripe customer."""
        customer = stripe.Customer.retrieve(provider_customer_id)
        return customer
    
    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session."""
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata or {},
            subscription_data={
                'metadata': metadata or {}
            }
        )
        
        return {
            'checkout_session_id': session.id,
            'checkout_url': session.url,
            'expires_at': datetime.fromtimestamp(session.expires_at)
        }
    
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a Stripe subscription."""
        params = {
            'customer': customer_id,
            'items': [{'price': price_id}],
            'metadata': metadata or {},
        }
        
        if trial_days:
            params['trial_period_days'] = trial_days
        
        subscription = stripe.Subscription.create(**params)
        
        return {
            'provider_subscription_id': subscription.id,
            'status': subscription.status,
            'current_period_start': datetime.fromtimestamp(subscription.current_period_start),
            'current_period_end': datetime.fromtimestamp(subscription.current_period_end),
            'trial_end': datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None
        }
    
    async def get_subscription(self, provider_subscription_id: str) -> Dict[str, Any]:
        """Retrieve Stripe subscription."""
        subscription = stripe.Subscription.retrieve(provider_subscription_id)
        return subscription
    
    async def update_subscription(
        self,
        provider_subscription_id: str,
        new_price_id: str,
        proration_behavior: str = "create_prorations"
    ) -> Dict[str, Any]:
        """Update Stripe subscription (upgrade/downgrade)."""
        subscription = stripe.Subscription.retrieve(provider_subscription_id)
        
        subscription = stripe.Subscription.modify(
            provider_subscription_id,
            items=[{
                'id': subscription['items']['data'][0].id,
                'price': new_price_id,
            }],
            proration_behavior=proration_behavior
        )
        
        return subscription
    
    async def cancel_subscription(
        self,
        provider_subscription_id: str,
        at_period_end: bool = True
    ) -> Dict[str, Any]:
        """Cancel Stripe subscription."""
        if at_period_end:
            subscription = stripe.Subscription.modify(
                provider_subscription_id,
                cancel_at_period_end=True
            )
        else:
            subscription = stripe.Subscription.cancel(provider_subscription_id)
        
        return {
            'provider_subscription_id': subscription.id,
            'status': subscription.status,
            'cancel_at_period_end': subscription.cancel_at_period_end,
            'canceled_at': datetime.fromtimestamp(subscription.canceled_at) if subscription.canceled_at else None
        }
    
    async def create_customer_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> Dict[str, Any]:
        """Create Stripe Customer Portal session."""
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )
        
        return {
            'portal_url': session.url,
            'expires_at': None  # Portal sessions don't expire
        }
    
    async def list_invoices(
        self,
        customer_id: str,
        limit: int = 10
    ) -> list[Dict[str, Any]]:
        """List Stripe invoices for a customer."""
        invoices = stripe.Invoice.list(
            customer=customer_id,
            limit=limit
        )
        
        return [{
            'provider_invoice_id': inv.id,
            'amount_due': inv.amount_due,
            'amount_paid': inv.amount_paid,
            'currency': inv.currency,
            'status': inv.status,
            'invoice_pdf': inv.invoice_pdf,
            'hosted_invoice_url': inv.hosted_invoice_url,
            'created_at': datetime.fromtimestamp(inv.created)
        } for inv in invoices.data]
    
    async def get_invoice(self, provider_invoice_id: str) -> Dict[str, Any]:
        """Retrieve Stripe invoice."""
        invoice = stripe.Invoice.retrieve(provider_invoice_id)
        return invoice
    
    async def verify_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """
        Verify Stripe webhook signature and parse event.
        
        Raises:
            ValueError: If signature verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            return {
                'event_id': event.id,
                'event_type': event.type,
                'data': event.data.object
            }
        except ValueError as e:
            # Invalid payload
            raise ValueError(f"Invalid payload: {str(e)}")
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            raise ValueError(f"Invalid signature: {str(e)}")
    
    async def add_payment_method(
        self,
        customer_id: str,
        payment_method_token: str
    ) -> Dict[str, Any]:
        """Attach payment method to Stripe customer."""
        payment_method = stripe.PaymentMethod.attach(
            payment_method_token,
            customer=customer_id
        )
        
        # Extract card details if it's a card
        details = {}
        if payment_method.type == 'card':
            card = payment_method.card
            details = {
                'brand': card.brand,
                'last4': card.last4,
                'exp_month': card.exp_month,
                'exp_year': card.exp_year
            }
        
        return {
            'provider_payment_method_id': payment_method.id,
            'type': payment_method.type,
            'details': details
        }
    
    async def set_default_payment_method(
        self,
        customer_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """Set default payment method for Stripe customer."""
        customer = stripe.Customer.modify(
            customer_id,
            invoice_settings={
                'default_payment_method': payment_method_id
            }
        )
        
        return customer
