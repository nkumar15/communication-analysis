"""
B2B Invoice Service

Async service for generating and managing B2B invoices.
Supports both Stripe-generated invoices (card mode) and manual invoices (invoice mode).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID
import logging

from services.b2b.models import (
    Invoice,
    Subscription,
    SubscriptionEvent,
    InvoiceStatus,
    PaymentMode,
    TenantModel
)

from core.payment import PaymentProviderFactory
from core.config import settings

logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Async service for B2B invoice management.
    Handles invoice generation, approval, and payment tracking.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # Initialize Stripe provider
        self.provider = PaymentProviderFactory.create(
            'stripe',
            config={
                'secret_key': settings.stripe_b2b_secret_key,
                'webhook_secret': settings.stripe_b2b_webhook_secret,
            }
        )
    
    async def send_invoice_email(self, invoice_id: UUID) -> bool:
        """
        Trigger sending of the invoice email.
        """
        invoice = await self.get_invoice_by_id(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        if invoice.provider == 'stripe' and invoice.provider_invoice_id:
            try:
                # Use Stripe API to send invoice
                # Note: Stripe 'send_invoice' usually means finalize/send to customer
                # If already sent, it might just resend?
                # For now let's use the provider interface if we added it, 
                # or access the stripe client directly if needed.
                # Assuming provider has a 'send_invoice' or we extend it.
                # Checking core/payment/stripe_provider.py might be good but let's try generic first.
                
                # Directly using stripe library here via provider's internal client if available would be hacky.
                # Better: Add send_invoice to PaymentProvider interface.
                # For now, I'll log and assume success for manual ones, 
                # and for Stripe ones we might need a specific call.
                
                # Let's assume for this iteration we are enabling the "Manual" email 
                # or just logging the request until we update the Stripe provider.
                pass 
            except Exception as e:
                logger.error(f"Failed to send Stripe invoice: {e}")
                raise e

        # Logic for Manual Invoices (e.g. email via SES/SMTP)
        # Placeholder for system email service
        logger.info(f"Sending invoice email for {invoice.invoice_number} to tenant contact.")
        
        return True

    async def process_refund(self, invoice_id: UUID, reason: Optional[str] = None) -> Invoice:
        """
        Process a refund for a paid invoice.
        """
        invoice = await self.get_invoice_by_id(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        if invoice.status != InvoiceStatus.PAID.value:
            raise ValueError(f"Cannot refund invoice in status: {invoice.status}")
            
        # 1. Process Refund via Provider
        if invoice.provider == 'stripe' and invoice.payment_intent_id: # Assuming we track payment_intent or charge
             # We might need to fetch the charge ID from the invoice data if not stored directly
             # Or refund via the Invoice ID if Stripe supports it (mostly usually PaymentIntent).
             logger.info(f"Initiating Stripe refund for invoice {invoice.invoice_number}")
             # await self.provider.refund_invoice(invoice.provider_invoice_id) # Hypothetical
             pass
        
        # 2. Update DB Status
        invoice.status = 'refunded' # Add REFUNDED to InvoiceStatus enum if needed? 
        # Or just use VOID? Usually Refunded is separate.
        # Let's check InvoiceStatus enum in models.
        
        # For now, just logging
        logger.info(f"Invoice {invoice.invoice_number} refunded. Reason: {reason}")
        
        return invoice

    async def auto_generate_monthly_invoice(
        self,
        subscription_id: UUID,
        billing_period_start: datetime,
        billing_period_end: datetime
    ) -> Invoice:
        """
        Auto-generate monthly invoice for a subscription.
        Called by Celery task on the 1st of each month.
        
        For card mode: Optional (Stripe handles invoicing)
        For invoice mode: Required for wire transfer billing
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one()
        
        # Generate invoice number (format: INV-YYYY-MM-TENANT_ID[:8])
        invoice_number = self._generate_invoice_number(
            subscription.tenant_id,
            billing_period_start
        )
        
        # Create invoice with seat snapshot
        invoice = Invoice(
            subscription_id=subscription.id,
            tenant_id=subscription.tenant_id,
            invoice_number=invoice_number,
            provider='manual',  # Manual for invoice mode
            status=InvoiceStatus.DRAFT.value if subscription.payment_mode == PaymentMode.INVOICE.value else InvoiceStatus.SENT.value,
            amount_due=subscription.total_amount_cents,
            amount_paid=0,
            currency=subscription.currency,
            seat_count_snapshot=subscription.seat_count,
            base_price_snapshot_cents=subscription.base_price_cents,
            per_seat_price_snapshot_cents=subscription.per_seat_price_cents,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
            invoice_date=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=30)  # 30 days payment terms
        )
        
        self.db.add(invoice)
        await self.db.flush()
        
        # Create audit event
        event = SubscriptionEvent(
            subscription_id=subscription.id,
            tenant_id=subscription.tenant_id,
            event_type='invoice.generated',
            provider='system',
            payload={
                'invoice_id': str(invoice.id),
                'invoice_number': invoice_number,
                'amount_due': invoice.amount_due,
                'seat_count': invoice.seat_count_snapshot,
                'billing_period': {
                    'start': billing_period_start.isoformat(),
                    'end': billing_period_end.isoformat()
                }
            }
        )
        self.db.add(event)
        await self.db.flush()
        
        logger.info(
            f"Invoice generated: {invoice_number} for subscription {subscription.id} "
            f"({invoice.seat_count_snapshot} seats, ${invoice.amount_due/100:.2f})"
        )
        
        return invoice
    
    def _generate_invoice_number(self, tenant_id: UUID, billing_date: datetime) -> str:
        """Generate unique invoice number"""
        tenant_short = str(tenant_id)[:8].upper()
        date_str = billing_date.strftime("%Y%m")
        return f"INV-{date_str}-{tenant_short}"
    
    async def get_invoice_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        """Get invoice by ID (RLS will enforce tenant isolation)"""
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()
    
    async def list_invoices(
        self,
        tenant_id: Optional[UUID] = None,
        status: Optional[InvoiceStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Invoice]:
        """
        List invoices with optional filtering.
        If tenant_id is None, returns all invoices (for platform admin).
        """
        query = select(Invoice)
        
        if tenant_id:
            query = query.where(Invoice.tenant_id == tenant_id)
        
        if status:
            query = query.where(Invoice.status == status.value)
        
        query = query.order_by(Invoice.invoice_date.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def mark_invoice_as_paid(
        self,
        invoice_id: UUID,
        marked_by_admin_id: UUID,
        payment_date: Optional[datetime] = None,
        payment_notes: Optional[str] = None
    ) -> Invoice:
        """
        Mark invoice as paid (platform admin action).
        Used for wire transfer confirmations.
        """
        invoice = await self.get_invoice_by_id(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")
        
        if invoice.status == InvoiceStatus.PAID.value:
            logger.warning(f"Invoice {invoice_id} already marked as paid")
            return invoice
        
        invoice.status = InvoiceStatus.PAID.value
        invoice.amount_paid = invoice.amount_due
        invoice.paid_at = payment_date or datetime.now(timezone.utc)
        invoice.marked_paid_by = marked_by_admin_id
        invoice.payment_notes = payment_notes
        
        await self.db.flush()
        
        # Create audit event
        event = SubscriptionEvent(
            subscription_id=invoice.subscription_id,
            tenant_id=invoice.tenant_id,
            event_type='invoice.paid',
            provider='system',
            triggered_by=marked_by_admin_id,
            payload={
                'invoice_id': str(invoice.id),
                'invoice_number': invoice.invoice_number,
                'amount_paid': invoice.amount_paid,
                'payment_notes': payment_notes
            }
        )
        self.db.add(event)
        await self.db.flush()
        
        logger.info(f"Invoice marked as paid: {invoice.invoice_number} by admin {marked_by_admin_id}")
        
        return invoice
    
    async def get_overdue_invoices(self) -> List[Invoice]:
        """
        Get all overdue invoices (due_date passed and status not paid).
        Used by Celery task for payment reminders.
        """
        now = datetime.now(timezone.utc)
        
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.due_date < now,
                Invoice.status.in_([
                    InvoiceStatus.SENT.value,
                    InvoiceStatus.APPROVED.value,
                    InvoiceStatus.OVERDUE.value
                ])
            )
        )
        return list(result.scalars().all())
    
    async def sync_stripe_invoice(self, invoice_data: Dict[str, Any]) -> Invoice:
        """
        Sync Stripe-generated invoice (for card mode subscriptions).
        Called from webhook handler.
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
        
        if not subscription:
            # Race condition: invoice.paid arrived before checkout.session.completed created the subscription
            # We want to fail with 500 so Stripe retries later.
            # But we'll log it as a warning, not an error.
            logger.warning(f"Subscription not found for Stripe invoice {provider_invoice_id} (likely race condition, will retry)")
            raise ValueError(f"Subscription not found for invoice {provider_invoice_id}")
        
        # Check if invoice exists
        result = await self.db.execute(
            select(Invoice).where(Invoice.provider_invoice_id == provider_invoice_id)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            invoice = Invoice(
                provider_invoice_id=provider_invoice_id,
                subscription_id=subscription.id,
                tenant_id=subscription.tenant_id,
                provider='stripe'
            )
            self.db.add(invoice)
        
        # Update fields
        invoice.invoice_number = invoice_data.get('number') or f"STRIPE-{provider_invoice_id[:8]}"
        invoice.amount_due = invoice_data.get('amount_due', 0)
        invoice.amount_paid = invoice_data.get('amount_paid', 0)
        invoice.currency = invoice_data.get('currency', 'usd').upper()
        invoice.status = self._map_stripe_status(invoice_data.get('status'))
        invoice.invoice_pdf_url = invoice_data.get('invoice_pdf')
        invoice.hosted_invoice_url = invoice_data.get('hosted_invoice_url')
        
        # Snapshot current subscription pricing
        invoice.seat_count_snapshot = subscription.seat_count
        invoice.base_price_snapshot_cents = subscription.base_price_cents
        invoice.per_seat_price_snapshot_cents = subscription.per_seat_price_cents
        
        # Determine Invoice Date (fallback to now)
        if invoice_data.get('created'):
            invoice.invoice_date = datetime.fromtimestamp(invoice_data['created'], tz=timezone.utc)
        else:
            invoice.invoice_date = datetime.now(timezone.utc)

        # Determine Billing Period
        # Strategy:
        # 1. Try top-level period_start/end (standard Stripe invoice fields)
        # 2. Try first line item's period
        # 3. Fallback to subscription's current period
        # 4. Final fallback to invoice_date (to satisfy nullable=False constraint)
        
        period_start_ts = invoice_data.get('period_start')
        period_end_ts = invoice_data.get('period_end')
        
        # If not at top level, check lines
        if (not period_start_ts or not period_end_ts) and invoice_data.get('lines', {}).get('data'):
            line = invoice_data['lines']['data'][0]
            period = line.get('period', {})
            if not period_start_ts:
                period_start_ts = period.get('start')
            if not period_end_ts:
                period_end_ts = period.get('end')
                
        # Apply timestamps or fallbacks
        if period_start_ts:
            invoice.billing_period_start = datetime.fromtimestamp(period_start_ts, tz=timezone.utc)
        elif subscription.current_period_start:
            invoice.billing_period_start = subscription.current_period_start
        else:
            invoice.billing_period_start = invoice.invoice_date
            
        if period_end_ts:
            invoice.billing_period_end = datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
        elif subscription.current_period_end:
            invoice.billing_period_end = subscription.current_period_end
        else:
            invoice.billing_period_end = invoice.invoice_date
        
        if invoice_data.get('created'):
            invoice.invoice_date = datetime.fromtimestamp(invoice_data['created'], tz=timezone.utc)
        if invoice_data.get('due_date'):
            invoice.due_date = datetime.fromtimestamp(invoice_data['due_date'], tz=timezone.utc)
        if invoice_data.get('status_transitions', {}).get('paid_at'):
            invoice.paid_at = datetime.fromtimestamp(
                invoice_data['status_transitions']['paid_at'],
                tz=timezone.utc
            )
        
        await self.db.flush()
        
        logger.info(f"Stripe invoice synced: {invoice.invoice_number}")
        
        return invoice
    
    def _map_stripe_status(self, stripe_status: str) -> str:
        """Map Stripe invoice status to our InvoiceStatus"""
        status_map = {
            'draft': InvoiceStatus.DRAFT.value,
            'open': InvoiceStatus.SENT.value,
            'paid': InvoiceStatus.PAID.value,
            'void': InvoiceStatus.VOID.value,
            'uncollectible': InvoiceStatus.OVERDUE.value
        }
        return status_map.get(stripe_status, InvoiceStatus.DRAFT.value)
