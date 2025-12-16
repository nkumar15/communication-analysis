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

from core.payment import PaymentProviderFactory
from core.config import settings
from services.b2b.models import (
    Subscription,
    SubscriptionEvent,
    SubscriptionTier,
    PaymentMode,
    SubscriptionStatus,
    TenantModel
)
from services.b2b.models.user import UserModel

logger = logging.getLogger(__name__)


# Pricing Matrix (in cents)
# TODO: Move to database or config file for production
PRICING_MATRIX = {
    SubscriptionTier.STARTER: {
        'monthly': {'base': 0, 'per_seat': 1000},  # $0 base + $10/seat
        'yearly': {'base': 0, 'per_seat': 10000}   # $0 base + $100/seat
    },
    SubscriptionTier.PROFESSIONAL: {
        'monthly': {'base': 5000, 'per_seat': 2000},  # $50 base + $20/seat
        'yearly': {'base': 50000, 'per_seat': 20000}  # $500 base + $200/seat
    },
    SubscriptionTier.ENTERPRISE: {
        'monthly': {'base': 20000, 'per_seat': 5000},  # $200 base + $50/seat
        'yearly': {'base': 200000, 'per_seat': 50000}  # $2000 base + $500/seat
    }
}


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
    
    def calculate_seat_based_pricing(
        self, 
        tier: SubscriptionTier, 
        seat_count: int, 
        billing_interval: str
    ) -> Dict[str, int]:
        """
        Calculate pricing based on base + per-seat model.
        
        Returns:
            {
                'base_price_cents': int,
                'per_seat_price_cents': int,
                'total_amount_cents': int
            }
        """
        pricing = PRICING_MATRIX.get(tier, {}).get(billing_interval)
        if not pricing:
            raise ValueError(f"Invalid tier or billing interval: {tier}, {billing_interval}")
        
        base_price = pricing['base']
        per_seat_price = pricing['per_seat']
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
        
        # Get or create Stripe customer
        subscription = await self.get_tenant_subscription(tenant_id)
        
        # Get tenant for customer creation
        tenant_result = await self.db.execute(
            select(TenantModel).where(TenantModel.id == tenant_id)
        )
        tenant = tenant_result.scalar_one()
        
        customer_id = subscription.provider_customer_id if subscription else None
        
        if not customer_id:
            # Create Stripe customer
            logger.info(f"Creating Stripe customer for tenant {tenant_id}")
            customer_result = await self.provider.create_customer(
                user_id=str(tenant_id),
                email=f"billing@{tenant.domain}",
                name=tenant.name,
                metadata={'tenant_id': str(tenant_id)}
            )
            customer_id = customer_result['provider_customer_id']
        
        # Calculate pricing
        seat_count = await self.get_active_seat_count(tenant_id)
        pricing = self.calculate_seat_based_pricing(tier, seat_count, billing_interval)
        
        # Get Stripe price ID from settings
        price_id = getattr(
            settings,
            f'stripe_b2b_price_{tier.value}_{billing_interval}',
            None
        )
        if not price_id:
            raise ValueError(f"Stripe price ID not configured for {tier.value} {billing_interval}")
        
        # Default URLs
        if not success_url:
            success_url = f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        if not cancel_url:
            cancel_url = f"{settings.frontend_url}/billing"
        
        # Create checkout session
        logger.info(f"Creating checkout for tenant {tenant_id}, tier {tier.value}, seats {seat_count}")
        
        metadata = {
            'tenant_id': str(tenant_id),
            'tier': tier.value,
            'billing_interval': billing_interval,
            'seat_count': seat_count,
            'pricing_snapshot': str(pricing)
        }
        
        result = await self.provider.create_checkout_session(
            customer_id=customer_id,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            quantity=seat_count  # Stripe quantity for per-seat pricing
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
        
        # Get subscription data from Stripe
        provider_subscription_id = session_data.get('subscription')
        subscription_data = await self.provider.get_subscription(provider_subscription_id)
        
        # Calculate pricing
        pricing = self.calculate_seat_based_pricing(tier, seat_count, billing_interval)
        
        # Update or create subscription
        subscription = await self.get_tenant_subscription(tenant_id)
        
        if not subscription:
            subscription = Subscription(tenant_id=tenant_id)
            self.db.add(subscription)
        
        # Update subscription fields
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
        subscription.current_period_start = datetime.fromtimestamp(
            subscription_data['current_period_start'], 
            tz=timezone.utc
        )
        subscription.current_period_end = datetime.fromtimestamp(
            subscription_data['current_period_end'],
            tz=timezone.utc
        )
        
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
        
        logger.info(f"Subscription activated: {subscription.id} (tier: {tier.value}, seats: {seat_count})")
        
        return subscription
    
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
            pricing = self.calculate_seat_based_pricing(
                SubscriptionTier(subscription.tier),
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
        
        return subscription
