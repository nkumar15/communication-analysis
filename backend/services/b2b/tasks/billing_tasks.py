"""
B2B Billing Celery Tasks

Background tasks for automated invoice generation, seat count updates, and email notifications.
"""
from celery import shared_task
from core.tasks.celery_app import celery_app
from core.database import AsyncSessionLocal
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from uuid import UUID
import asyncio
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def auto_generate_monthly_invoices(self):
    """
    Auto-generate monthly invoices for all active subscriptions.
    Scheduled to run on the 1st of each month at midnight.
    
    Cron: 0 0 1 * * (1st day of month at 00:00)
    """
    logger.info("Starting monthly invoice generation...")
    
    async def _generate_invoices():
        from services.b2b.models import Subscription, PaymentMode, SubscriptionStatus
        from services.b2b.services.invoice_service import InvoiceService
        
        async with AsyncSessionLocal() as db:
            # Get all active subscriptions (both card and invoice mode)
            result = await db.execute(
                select(Subscription).where(
                    Subscription.status == SubscriptionStatus.ACTIVE.value
                )
            )
            subscriptions = result.scalars().all()
            
            invoice_service = InvoiceService(db)
            
            # Calculate billing period (previous month)
            now = datetime.now(timezone.utc)
            billing_period_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            billing_period_start = (billing_period_end - timedelta(days=1)).replace(day=1)
            
            generated_count = 0
            failed_count = 0
            
            for subscription in subscriptions:
                try:
                    # Generate invoice
                    invoice = await invoice_service.auto_generate_monthly_invoice(
                        subscription_id=subscription.id,
                        billing_period_start=billing_period_start,
                        billing_period_end=billing_period_end
                    )
                    
                    generated_count += 1
                    logger.info(f"Generated invoice {invoice.invoice_number} for tenant {subscription.tenant_id}")
                    
                    # For invoice mode, send email notification
                    if subscription.payment_mode == PaymentMode.INVOICE.value:
                        # TODO: Trigger email task
                        pass
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to generate invoice for subscription {subscription.id}: {e}")
            
            await db.commit()
            
            logger.info(
                f"Invoice generation complete: {generated_count} success, {failed_count} failed "
                f"(total: {len(subscriptions)})"
            )
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_generate_invoices())
        loop.close()
    except Exception as exc:
        logger.error(f"Invoice generation failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2)
def recalculate_seat_counts(self):
    """
    Recalculate seat counts for all active subscriptions.
    Scheduled to run daily to sync seat counts with active users.
    
    Cron: 0 2 * * * (daily at 02:00)
    """
    logger.info("Starting seat count recalculation...")
    
    async def _recalculate():
        from services.b2b.models import Subscription, SubscriptionStatus
        from services.b2b.services.subscription_service import SubscriptionService
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.status == SubscriptionStatus.ACTIVE.value
                )
            )
            subscriptions = result.scalars().all()
            
            service = SubscriptionService(db)
            updated_count = 0
            
            for subscription in subscriptions:
                try:
                    old_count = subscription.seat_count
                    await service.update_seat_count(subscription.id)
                    
                    # Refresh to get updated value
                    await db.refresh(subscription)
                    
                    if subscription.seat_count != old_count:
                        updated_count += 1
                        logger.info(
                            f"Updated seat count for subscription {subscription.id}: "
                            f"{old_count} → {subscription.seat_count}"
                        )
                except Exception as e:
                    logger.error(f"Failed to update seat count for subscription {subscription.id}: {e}")
            
            await db.commit()
            
            logger.info(f"Seat count recalculation complete: {updated_count} updated")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_recalculate())
        loop.close()
    except Exception as exc:
        logger.error(f"Seat count recalculation failed: {exc}")
        raise self.retry(exc=exc)
