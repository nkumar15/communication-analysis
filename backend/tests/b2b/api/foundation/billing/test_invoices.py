"""
E2E Tests for B2B Invoice Management
Standardized version following project testing rules.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from modules.b2b.models import (
    Subscription,
    Invoice,
    SubscriptionTier,
    PaymentMode,
    SubscriptionStatus,
    InvoiceStatus
)
from modules.b2b.services.invoice_service import InvoiceService
from tests.conftest import (
    create_test_user,
    create_test_tenant,
    create_mock_firebase_token,
    encode_mock_jwt
)

@pytest.mark.asyncio
class TestInvoiceManagement:
    """
    Standardized tests for invoice generation, listing, and payment tracking.
    Uses b2b_test_setup for consistent tenant isolation and RLS context.
    """
    
    async def test_auto_generate_monthly_invoice_success(self, b2b_test_setup, db_session):
        """Test automatic monthly invoice generation"""
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        tenant_session = setup["session"]
        
        # Create subscription (via tenant session to ensure RLS)
        subscription = Subscription(
            tenant_id=tenant_id,
            tier=SubscriptionTier.PROFESSIONAL.value,
            payment_mode=PaymentMode.INVOICE.value,
            status=SubscriptionStatus.ACTIVE.value,
            seat_count=5,
            base_price_cents=5000,
            per_seat_price_cents=2000,
            total_amount_cents=15000
        )
        tenant_session.add(subscription)
        await tenant_session.flush()
        
        # Action
        invoice_service = InvoiceService(db_session)
        billing_period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        billing_period_end = billing_period_start + timedelta(days=30)
        
        invoice = await invoice_service.auto_generate_monthly_invoice(
            subscription_id=subscription.id,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end
        )
        await tenant_session.commit()
        
        # Verify via tenant session
        result = await tenant_session.execute(select(Invoice).where(Invoice.id == invoice.id))
        verified_invoice = result.scalar_one()
        
        assert verified_invoice.subscription_id == subscription.id
        assert verified_invoice.tenant_id == tenant_id
        assert verified_invoice.amount_due == 15000
        assert "INV-" in verified_invoice.invoice_number

    async def test_list_invoices_success(self, api_client, b2b_test_setup):
        """Test listing invoices via API
        
        Note: Requires billing:read permission which only owner role has.
        """
        setup = b2b_test_setup
        tenant = setup["tenant"]
        tenant_id = setup["tenant_id"]
        tenant_session = setup["session"]
        
        # Create OWNER user (has billing:read permission)
        owner = await create_test_user(
            tenant_session,
            tenant_id=tenant.id,
            email=f"owner_inv@{tenant.domain}",
            role_slug="owner"
        )
        owner_token = encode_mock_jwt(create_mock_firebase_token(
            uid=owner.firebase_uid,
            email=owner.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Setup data
        subscription = Subscription(
            tenant_id=tenant_id,
            tier=SubscriptionTier.PROFESSIONAL.value,
            seat_count=3,
            total_amount_cents=11000
        )
        tenant_session.add(subscription)
        await tenant_session.flush()
        
        invoice = Invoice(
            subscription_id=subscription.id,
            tenant_id=tenant_id,
            invoice_number=f"INV-{uuid4().hex[:8].upper()}",
            status=InvoiceStatus.SENT.value,
            amount_due=11000,
            seat_count_snapshot=3,
            base_price_snapshot_cents=5000,
            per_seat_price_snapshot_cents=2000,
            billing_period_start=datetime.now(timezone.utc),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            invoice_date=datetime.now(timezone.utc)
        )
        tenant_session.add(invoice)
        await tenant_session.commit()
        
        # API Call (using OWNER token - required for billing:read)
        response = await api_client.get(
            "/api/b2b/billing/invoices",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(inv["id"] == str(invoice.id) for inv in data)

    async def test_get_invoice_detail_success(self, api_client, b2b_test_setup):
        """Test getting a single invoice by ID
        
        Note: Requires billing:read permission which only owner role has.
        """
        setup = b2b_test_setup
        tenant = setup["tenant"]
        tenant_id = setup["tenant_id"]
        tenant_session = setup["session"]
        
        # Create OWNER user (has billing:read permission)
        owner = await create_test_user(
            tenant_session,
            tenant_id=tenant.id,
            email=f"owner_detail@{tenant.domain}",
            role_slug="owner"
        )
        owner_token = encode_mock_jwt(create_mock_firebase_token(
            uid=owner.firebase_uid,
            email=owner.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        subscription = Subscription(
            tenant_id=tenant_id,
            tier=SubscriptionTier.PROFESSIONAL.value,
            seat_count=5,
            total_amount_cents=15000
        )
        tenant_session.add(subscription)
        await tenant_session.flush()
        
        invoice = Invoice(
            subscription_id=subscription.id,
            tenant_id=tenant_id,
            invoice_number=f"INV-DETAIL-{uuid4().hex[:8].upper()}",
            status=InvoiceStatus.SENT.value,
            amount_due=15000,
            seat_count_snapshot=5,
            base_price_snapshot_cents=5000,
            per_seat_price_snapshot_cents=2000,
            billing_period_start=datetime.now(timezone.utc),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            invoice_date=datetime.now(timezone.utc)
        )
        tenant_session.add(invoice)
        await tenant_session.commit()
        
        # Action (using OWNER token - required for billing:read)
        response = await api_client.get(
            f"/api/b2b/billing/invoices/{invoice.id}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(invoice.id)
        assert data["amount_due"] == 15000

    async def test_get_invoice_unauthorized(self, api_client):
        """Rule 7: Test unauthorized access (no token)"""
        response = await api_client.get(f"/api/b2b/billing/invoices/{uuid4()}")
        assert response.status_code == 401

    async def test_get_invoice_not_found(self, api_client, b2b_test_setup):
        """Rule 7: Test non-existent invoice (404)
        
        Note: Requires billing:read permission which only owner role has.
        """
        setup = b2b_test_setup
        tenant = setup["tenant"]
        
        # Create OWNER user (has billing:read permission)
        owner = await create_test_user(
            setup['session'],
            tenant_id=tenant.id,
            email=f"owner_notfound@{tenant.domain}",
            role_slug="owner"
        )
        owner_token = encode_mock_jwt(create_mock_firebase_token(
            uid=owner.firebase_uid,
            email=owner.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.get(
            f"/api/b2b/billing/invoices/{uuid4()}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 404

    async def test_invoice_tenant_isolation(self, api_client, b2b_test_setup, db_session):
        """Rule 7: Test that tenant cannot access another tenant's invoice
        
        Note: Requires billing:read permission which only owner role has.
        """
        from tests.conftest import create_test_tenant
        from modules.b2b.models import Invoice, Subscription, SubscriptionTier, PaymentMode, SubscriptionStatus
        
        # Setup: Current tenant (A)
        setup_a = b2b_test_setup
        tenant_a = setup_a["tenant"]
        
        # Create OWNER user for tenant A (has billing:read permission)
        owner_a = await create_test_user(
            setup_a['session'],
            tenant_id=tenant_a.id,
            email=f"owner_iso@{tenant_a.domain}",
            role_slug="owner"
        )
        owner_a_token = encode_mock_jwt(create_mock_firebase_token(
            uid=owner_a.firebase_uid,
            email=owner_a.email,
            firebase_tenant_id=tenant_a.firebase_tenant_id
        ))
        
        # Setup: Another tenant (B)
        tenant_b = await create_test_tenant(db_session)
        # MUST create a real subscription for tenant B to satisfy FK and Unique constraints
        sub_b = Subscription(
            tenant_id=tenant_b.id,
            tier=SubscriptionTier.PROFESSIONAL.value,
            payment_mode=PaymentMode.INVOICE.value,
            status=SubscriptionStatus.ACTIVE.value,
            seat_count=1,
            total_amount_cents=5000
        )
        db_session.add(sub_b)
        await db_session.flush()
        
        # Create invoice for Tenant B
        invoice_b = Invoice(
            tenant_id=tenant_b.id,
            subscription_id=sub_b.id,
            invoice_number=f"INV-ISOLATION-{uuid4().hex[:8].upper()}",
            status=InvoiceStatus.SENT.value,
            amount_due=5000,
            seat_count_snapshot=1,
            base_price_snapshot_cents=5000,
            per_seat_price_snapshot_cents=0,
            billing_period_start=datetime.now(timezone.utc),
            billing_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            invoice_date=datetime.now(timezone.utc)
        )
        db_session.add(invoice_b)
        await db_session.flush()
        
        # Action: Tenant A owner tries to access Tenant B's invoice
        response = await api_client.get(
            f"/api/b2b/billing/invoices/{invoice_b.id}",
            headers={"Authorization": f"Bearer {owner_a_token}"}
        )
        
        # Assert: Should return 404 owing to RLS isolation
        assert response.status_code == 404
