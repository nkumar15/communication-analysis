"""
E2E Tests for B2B Invoice Management

Tests invoice generation, listing, and payment tracking with RLS.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from services.b2b.models import (
    Subscription,
    Invoice,
    SubscriptionTier,
    PaymentMode,
    SubscriptionStatus,
    InvoiceStatus
)
from services.b2b.services.invoice_service import InvoiceService


pytestmark = pytest.mark.asyncio


class TestInvoiceGeneration:
    """Test automated invoice generation"""
    
    async def test_auto_generate_monthly_invoice(
        self,
        db_session,
        b2b_tenant,
        rls_service
    ):
        """Test automatic monthly invoice generation"""
        await rls_service.set_tenant_context(db_session, b2b_tenant.id)
        
        # Create subscription
        subscription = Subscription(
            tenant_id=b2b_tenant.id,
            tier=SubscriptionTier.PROFESSIONAL.value,
            payment_mode=PaymentMode.INVOICE.value,
            status=SubscriptionStatus.ACTIVE.value,
            seat_count=5,
            base_price_cents=5000,
            per_seat_price_cents=2000,
            total_amount_cents=15000
        )
        db_session.add(subscription)
        await db_session.flush()
        
        # Generate invoice
        invoice_service = InvoiceService(db_session)
        
        billing_period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        billing_period_end = billing_period_start + timedelta(days=30)
        
        invoice = await invoice_service.auto_generate_monthly_invoice(
            subscription_id=subscription.id,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end
        )
        
        await db_session.commit()
        
        # Verify invoice
        assert invoice is not None
        assert invoice.subscription_id == subscription.id
        assert invoice.tenant_id == b2b_tenant.id
        assert invoice.amount_due == 15000
        assert invoice.seat_count_snapshot == 5
        assert invoice.base_price_snapshot_cents == 5000
        assert invoice.per_seat_price_snapshot_cents == 2000
        assert invoice.status == InvoiceStatus.DRAFT.value
        assert "INV-" in invoice.invoice_number
    
    async def test_invoice_number_format(
        self,
        db_session,
        b2b_tenant,
        rls_service
    ):
        """Test invoice number format: INV-YYYYMM-TENANTID"""
        await rls_service.set_tenant_context(db_session, b2b_tenant.id)
        
        subscription = Subscription(
            tenant_id=b2b_tenant.id,
            tier=SubscriptionTier.STARTER.value,
            seat_count=1,
            total_amount_cents=0
        )
        db_session.add(subscription)
        await db_session.flush()
        
        invoice_service = InvoiceService(db_session)
        
        now = datetime.now(timezone.utc)
        invoice = await invoice_service.auto_generate_monthly_invoice(
            subscription_id=subscription.id,
            billing_period_start=now,
            billing_period_end=now + timedelta(days=30)
        )
        
        await db_session.commit()
        
        # Verify format
        expected_prefix = f"INV-{now.strftime('%Y%m')}"
        assert invoice.invoice_number.startswith(expected_prefix)
        assert str(b2b_tenant.id)[:8].upper() in invoice.invoice_number


class TestInvoiceListing:
    """Test invoice listing and filtering"""
    
    async def test_list_invoices_by_status(
        self,
        db_session,
        b2b_tenant,
        rls_service
    ):
        """Test filtering invoices by status"""
        import secrets
        
        # Ensure RLS context is set BEFORE creating any data
        await rls_service.set_tenant_context(db_session, b2b_tenant.id)
        
        subscription = Subscription(
            tenant_id=b2b_tenant.id,
            tier=SubscriptionTier.PROFESSIONAL.value,
            seat_count=3,
            total_amount_cents=11000
        )
        db_session.add(subscription)
        await db_session.flush()
        
        # Create paid invoice with random number
        unique_suffix1 = secrets.token_hex(4).upper()
        paid_invoice = Invoice(
            subscription_id=subscription.id,
            tenant_id=b2b_tenant.id,
            invoice_number=f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-PAID-{unique_suffix1}",
            status=InvoiceStatus.PAID.value,
            amount_due=11000,
            amount_paid=11000,
            seat_count_snapshot=3,
            base_price_snapshot_cents=5000,
            per_seat_price_snapshot_cents=2000,
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=60),
            billing_period_end=datetime.now(timezone.utc) - timedelta(days=30),
            paid_at=datetime.now(timezone.utc) - timedelta(days=25),
            invoice_date=datetime.now(timezone.utc) - timedelta(days=60),
            due_date=datetime.now(timezone.utc) - timedelta(days=30)
        )
        
        # Create overdue invoice with random number
        unique_suffix2 = secrets.token_hex(4).upper()
        overdue_invoice = Invoice(
            subscription_id=subscription.id,
            tenant_id=b2b_tenant.id,
            invoice_number=f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-OD-{unique_suffix2}",
            status=InvoiceStatus.OVERDUE.value,
            amount_due=11000,
            amount_paid=0,
            seat_count_snapshot=3,
            base_price_snapshot_cents=5000,
            per_seat_price_snapshot_cents=2000,
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=30),
            billing_period_end=datetime.now(timezone.utc),
            invoice_date=datetime.now(timezone.utc) - timedelta(days=30), # Added invoice_date
            due_date=datetime.now(timezone.utc) - timedelta(days=5)
        )
        
        db_session.add(paid_invoice)
        db_session.add(overdue_invoice)
        await db_session.commit()
        
        # IMPORTANT: Reset RLS context after commit for queries
        await rls_service.set_tenant_context(db_session, b2b_tenant.id)
        
        # Test listing
        invoice_service = InvoiceService(db_session)
        
        # Get all invoices
        all_invoices = await invoice_service.list_invoices(tenant_id=b2b_tenant.id)
        assert len(all_invoices) == 2
        
        # Get only paid
        paid_invoices = await invoice_service.list_invoices(
            tenant_id=b2b_tenant.id,
            status=InvoiceStatus.PAID
        )
        assert len(paid_invoices) == 1
        assert paid_invoices[0].status == InvoiceStatus.PAID.value
        
        # Get only overdue
        overdue_invoices = await invoice_service.list_invoices(
            tenant_id=b2b_tenant.id,
            status=InvoiceStatus.OVERDUE
        )
        assert len(overdue_invoices) == 1
        assert overdue_invoices[0].status == InvoiceStatus.OVERDUE.value


class TestInvoicePayment:
    """Test invoice payment tracking"""
    
    async def test_mark_invoice_as_paid(
        self,
        db_session,
        b2b_tenant,
        rls_service
    ):
        """Test marking invoice as paid by platform admin"""
        import secrets
        from uuid import uuid4
        
        await rls_service.set_tenant_context(db_session, b2b_tenant.id)
        
        subscription = Subscription(
            tenant_id=b2b_tenant.id,
            tier=SubscriptionTier.ENTERPRISE.value,
            seat_count=10,
            total_amount_cents=70000
        )
        db_session.add(subscription)
        await db_session.flush()
        
        unique_suffix = secrets.token_hex(4).upper()
        invoice = Invoice(
            subscription_id=subscription.id,
            tenant_id=b2b_tenant.id,
            invoice_number=f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-PAY-{unique_suffix}",
            status=InvoiceStatus.SENT.value,
            amount_due=70000,
            amount_paid=0,
            seat_count_snapshot=10,
            base_price_snapshot_cents=20000,
            per_seat_price_snapshot_cents=5000,
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=30),
            billing_period_end=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=15),
            invoice_date=datetime.now(timezone.utc)  # Add missing required field
        )
        db_session.add(invoice)
        await db_session.commit()
        
        # Reset RLS context after commit
        await rls_service.set_tenant_context(db_session, b2b_tenant.id)
        
        # Mark as paid
        invoice_service = InvoiceService(db_session)
        
        payment_date = datetime.now(timezone.utc)
        payment_notes = "Wire transfer confirmed - Ref: WT123456"
        
        # Use a dummy UUID for platform admin (we removed FK constraint)
        platform_admin_id = uuid4()
        
        updated_invoice = await invoice_service.mark_invoice_as_paid(
            invoice_id=invoice.id,
            marked_by_admin_id=platform_admin_id,
            payment_date=payment_date,
            payment_notes=payment_notes
        )
        
        await db_session.commit()
        
        # Verify
        assert updated_invoice.status == InvoiceStatus.PAID.value
        assert updated_invoice.amount_paid == 70000
        assert updated_invoice.paid_at is not None
        assert updated_invoice.marked_paid_by == platform_admin_id
        assert updated_invoice.payment_notes == payment_notes
    
    async def test_get_overdue_invoices(
        self,
        db_session,
        b2b_tenant,
        rls_service
    ):
        """Test querying overdue invoices for a tenant"""
        import secrets
        
        # Create overdue invoice for tenant1
        await rls_service.set_tenant_context(db_session, b2b_tenant.id)
        
        subscription1 = Subscription(
            tenant_id=b2b_tenant.id,
            tier=SubscriptionTier.PROFESSIONAL.value,
            seat_count=5,
            total_amount_cents=15000
        )
        db_session.add(subscription1)
        await db_session.flush()
        
        unique_suffix1 = secrets.token_hex(4).upper()
        overdue1 = Invoice(
            subscription_id=subscription1.id,
            tenant_id=b2b_tenant.id,
            invoice_number=f"INV-T1-OD-{unique_suffix1}",
            status=InvoiceStatus.SENT.value,
            amount_due=15000,
            seat_count_snapshot=5,
            base_price_snapshot_cents=5000,
            per_seat_price_snapshot_cents=2000,
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=30),
            billing_period_end=datetime.now(timezone.utc),
            invoice_date=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=10)
        )
        db_session.add(overdue1)
        await db_session.commit()
        
        # Reset RLS context after commit
        await rls_service.set_tenant_context(db_session, b2b_tenant.id)
        
        # Query overdue invoices (within tenant scope)
        invoice_service = InvoiceService(db_session)
        overdue_invoices = await invoice_service.get_overdue_invoices()
        
        # Should find at least the one we created
        assert len(overdue_invoices) >= 1
        assert any(inv.invoice_number == f"INV-T1-OD-{unique_suffix1}" for inv in overdue_invoices)
        assert all(inv.tenant_id == b2b_tenant.id for inv in overdue_invoices)
