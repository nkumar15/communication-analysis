"""
Payment Provider Abstract Base Class

This module defines the abstract interface for payment providers.
Implementations for specific providers (Stripe, Razorpay, Xendit) should inherit from this class.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class PaymentProvider(ABC):
    """
    Abstract base class for payment providers.
    
    All payment providers must implement these methods to ensure consistent behavior
    across different payment gateways.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the payment provider with configuration.
        
        Args:
            config: Provider-specific configuration (API keys, secrets, etc.)
        """
        self.config = config
    
    @abstractmethod
    async def create_customer(
        self,
        user_id: str,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a customer in the payment provider's system.
        
        Args:
            user_id: Internal user ID
            email: Customer email
            name: Customer name
            metadata: Additional metadata to store
            
        Returns:
            {
                'provider_customer_id': str,
                'email': str,
                'created_at': datetime
            }
        """
        pass
    
    @abstractmethod
    async def get_customer(self, provider_customer_id: str) -> Dict[str, Any]:
        """
        Retrieve customer details.
        
        Args:
            provider_customer_id: Provider's customer ID
            
        Returns:
            Customer object from provider
        """
        pass
    
    @abstractmethod
    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None,
        quantity: int = 1,
        discounts: Optional[list[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create a checkout session for subscription purchase.
        
        Args:
            customer_id: Provider's customer ID
            price_id: Provider's price/plan ID
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment cancelled
            metadata: Additional metadata
            
        Returns:
            {
                'checkout_session_id': str,
                'checkout_url': str,
                'expires_at': datetime
            }
        """
        pass
    
    @abstractmethod
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        discounts: Optional[list[Dict[str, Any]]] = None,
        promotion_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a subscription directly (without checkout).
        
        Args:
            customer_id: Provider's customer ID
            price_id: Provider's price/plan ID
            trial_days: Number of trial days
            metadata: Additional metadata
            
        Returns:
            {
                'provider_subscription_id': str,
                'status': str,
                'current_period_start': datetime,
                'current_period_end': datetime
            }
        """
        pass
    
    @abstractmethod
    async def get_subscription(self, provider_subscription_id: str) -> Dict[str, Any]:
        """
        Retrieve subscription details.
        
        Args:
            provider_subscription_id: Provider's subscription ID
            
        Returns:
            Subscription object from provider
        """
        pass
    
    @abstractmethod
    async def update_subscription(
        self,
        provider_subscription_id: str,
        new_price_id: str,
        proration_behavior: str = "create_prorations"
    ) -> Dict[str, Any]:
        """
        Update subscription (upgrade/downgrade).
        
        Args:
            provider_subscription_id: Provider's subscription ID
            new_price_id: New price/plan ID
            proration_behavior: How to handle proration
            
        Returns:
            Updated subscription object
        """
        pass
    
    @abstractmethod
    async def cancel_subscription(
        self,
        provider_subscription_id: str,
        at_period_end: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            provider_subscription_id: Provider's subscription ID
            at_period_end: If True, cancel at end of billing period
            
        Returns:
            Updated subscription object with cancellation details
        """
        pass
    
    @abstractmethod
    async def create_customer_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> Dict[str, Any]:
        """
        Create a customer portal session for self-service.
        
        Args:
            customer_id: Provider's customer ID
            return_url: URL to return to after portal session
            
        Returns:
            {
                'portal_url': str,
                'expires_at': datetime
            }
        """
        pass
    
    @abstractmethod
    async def list_invoices(
        self,
        customer_id: str,
        limit: int = 10
    ) -> list[Dict[str, Any]]:
        """
        List invoices for a customer.
        
        Args:
            customer_id: Provider's customer ID
            limit: Maximum number of invoices to return
            
        Returns:
            List of invoice objects
        """
        pass
    
    @abstractmethod
    async def get_invoice(self, provider_invoice_id: str) -> Dict[str, Any]:
        """
        Retrieve a specific invoice.
        
        Args:
            provider_invoice_id: Provider's invoice ID
            
        Returns:
            Invoice object
        """
        pass
    
    @abstractmethod
    async def verify_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """
        Verify and parse a webhook event.
        
        Args:
            payload: Raw webhook payload
            signature: Webhook signature header
            
        Returns:
            {
                'event_id': str,
                'event_type': str,
                'data': dict
            }
            
        Raises:
            ValueError: If signature verification fails
        """
        pass
    
    @abstractmethod
    async def add_payment_method(
        self,
        customer_id: str,
        payment_method_token: str
    ) -> Dict[str, Any]:
        """
        Attach a payment method to a customer.
        
        Args:
            customer_id: Provider's customer ID
            payment_method_token: Payment method token from frontend
            
        Returns:
            {
                'provider_payment_method_id': str,
                'type': str,
                'details': dict (brand, last4, etc.)
            }
        """
        pass
    
    @abstractmethod
    async def set_default_payment_method(
        self,
        customer_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """
        Set default payment method for a customer.
        
        Args:
            customer_id: Provider's customer ID
            payment_method_id: Provider's payment method ID
            
        Returns:
            Updated customer object
        """
        pass
    
    @abstractmethod
    async def create_coupon(
        self,
        duration: str, # 'once', 'repeating', 'forever'
        name: Optional[str] = None,
        percent_off: Optional[float] = None,
        amount_off: Optional[int] = None,
        currency: Optional[str] = None,
        duration_in_months: Optional[int] = None,
        max_redemptions: Optional[int] = None,
        redeem_by: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a coupon in the provider's system.
        """
        pass
    
    @abstractmethod
    async def create_promotion_code(
        self,
        coupon_id: str,
        code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a customer-facing promotion code.
        """
        pass
