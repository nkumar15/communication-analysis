"""
Basic E2E Tests for B2B Billing API

Tests subscription and invoice endpoints with proper RLS context.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from modules.b2b.models import (
    Subscription,
    Invoice,
    SubscriptionTier,
    PaymentMode,
    SubscriptionStatus,
    InvoiceStatus
)


pytestmark = pytest.mark.asyncio


class TestSubscriptionAPI:
    """Test subscription endpoints"""
    
    async def test_get_subscription_starter_default(self, client, b2b_tenant, b2b_tenant_owner_token):
        """Test getting starter tier subscription (default)"""
        response = await client.get(
            "/api/b2b/billing/subscription",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "starter"
        assert data["tenant_id"] == str(b2b_tenant.id)
        assert "seat_count" in data
        assert data["seat_count"] >= 1
    
    async def test_create_checkout_professional(self, client, b2b_tenant, b2b_tenant_owner_token):
        """Test creating checkout session for professional tier"""
        response = await client.post(
            "/api/b2b/billing/checkout",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"},
            json={
                "tier": "professional",
                "billing_interval": "monthly"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "checkout_session_id" in data
        assert "checkout_url" in data
        assert "seat_count" in data
        assert "pricing" in data
        
        # Verify pricing structure
        pricing = data["pricing"]
        assert "base_price_cents" in pricing
        assert "per_seat_price_cents" in pricing
        assert "total_amount_cents" in pricing
        
        # Professional tier pricing (SGD)
        assert pricing["base_price_cents"] == 500000  # $5,000
        assert pricing["per_seat_price_cents"] == 200000  # $2,000
    
    async def test_create_checkout_starter_fails(self, client, b2b_tenant_owner_token):
        """Test that starter tier cannot be purchased (it's free)"""
        response = await client.post(
            "/api/b2b/billing/checkout",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"},
            json={
                "tier": "starter",
                "billing_interval": "monthly"
            }
        )
        
        assert response.status_code == 400
        assert "free" in response.json()["detail"].lower()


class TestInvoiceAPI:
    """Test invoice endpoints"""
    
    async def test_list_invoices_empty(self, client, b2b_tenant_owner_token):
        """Test listing invoices when none exist"""
        response = await client.get(
            "/api/b2b/billing/invoices",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    async def test_list_invoices_with_data(
        self, 
        client, 
        db_session, 
        b2b_tenant, 
        b2b_tenant_owner_token,
        rls_service
    ):
        """Test listing invoices with RLS enforcement"""
        import secrets
        
        # Set RLS context
        await rls_service.set_tenant_context(db_session, b2b_tenant.id)
        
        # Create test subscription
        subscription = Subscription(
            tenant_id=b2b_tenant.id,
            tier=SubscriptionTier.PROFESSIONAL.value,
            payment_mode=PaymentMode.INVOICE.value,
            status=SubscriptionStatus.ACTIVE.value,
            seat_count=5,
            base_price_cents=500000,  # $5,000
            per_seat_price_cents=200000,  # $2,000
            total_amount_cents=1500000  # $5,000 + ($2,000 * 5) = $15,000
        )
        db_session.add(subscription)
        await db_session.flush()
        
        # Generate unique invoice number
        unique_suffix = secrets.token_hex(4).upper()
        
        # Create test invoice
        invoice = Invoice(
            subscription_id=subscription.id,
            tenant_id=b2b_tenant.id,
            invoice_number=f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-TEST-{unique_suffix}",
            status=InvoiceStatus.SENT.value,
            amount_due=1500000,  # $15,000
            amount_paid=0,
            seat_count_snapshot=5,
            base_price_snapshot_cents=500000,  # $5,000
            per_seat_price_snapshot_cents=200000,  # $2,000
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=30),
            billing_period_end=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=30)
        )
        db_session.add(invoice)
        await db_session.commit()
        
        
        # Test API
        response = await client.get(
            "/api/b2b/billing/invoices",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # Check that invoice number follows the expected pattern with current date
        assert data[0]["invoice_number"].startswith(f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-TEST-")
        assert data[0]["status"] == "sent"
        assert data[0]["amount_due"] == 1500000  # $15,000
        assert data[0]["seat_count_snapshot"] == 5
    
    async def test_invoice_rls_isolation(
        self,
        client,
        db_session,
        b2b_tenant,
        b2b_tenant2,
        b2b_tenant_owner_token,
        rls_service
    ):
        """Test that tenants cannot access other tenants' invoices"""
        import secrets
        from sqlalchemy import select
        
        # Create invoice for tenant2
        await rls_service.set_tenant_context(db_session, b2b_tenant2.id)
        
        # Check if subscription exists for tenant2
        result = await db_session.execute(
            select(Subscription).where(Subscription.tenant_id == b2b_tenant2.id)
        )
        subscription2 = result.scalar_one_or_none()
        
        if not subscription2:
            subscription2 = Subscription(
                tenant_id=b2b_tenant2.id,
                tier=SubscriptionTier.PROFESSIONAL.value,
                seat_count=3,
                base_price_cents=500000,  # $5,000
                per_seat_price_cents=200000,  # $2,000
                total_amount_cents=1100000  # $5,000 + ($2,000 * 3) = $11,000
            )
            db_session.add(subscription2)
            await db_session.flush()
        
        # Generate unique invoice number
        unique_suffix = secrets.token_hex(4).upper()
        
        invoice2 = Invoice(
            subscription_id=subscription2.id,
            tenant_id=b2b_tenant2.id,
            invoice_number=f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-T2-{unique_suffix}",
            status=InvoiceStatus.SENT.value,
            amount_due=1100000,  # $11,000
            seat_count_snapshot=3,
            base_price_snapshot_cents=500000,  # $5,000
            per_seat_price_snapshot_cents=200000,  # $2,000
            billing_period_start=datetime.now(timezone.utc) - timedelta(days=30),
            billing_period_end=datetime.now(timezone.utc)
        )
        db_session.add(invoice2)
        await db_session.commit()
        
        # Try to access from tenant1
        response = await client.get(
            "/api/b2b/billing/invoices",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should not see tenant2's invoice
        assert len(data) == 0


class TestSeatCountCalculation:
    """Test seat count calculation logic"""
    
    async def test_seat_count_from_active_users(
        self,
        client,
        db_session,
        b2b_tenant,
        b2b_tenant_owner_token,
        rls_service
    ):
        """Test that seat count reflects active users"""
        from modules.b2b.models.user import UserModel
        
        await rls_service.set_tenant_context(db_session, b2b_tenant.id)
        
        # Add 3 more active users (1 already exists from fixture)
        for i in range(3):
            user = UserModel(
                tenant_id=b2b_tenant.id,
                email=f"user{i}@{b2b_tenant.domain}",
                name=f"User {i}",
                firebase_uid=f"test_uid_{i}",
                is_active=True
            )
            db_session.add(user)
        
        await db_session.commit()
        
        # Get subscription - should show 4 seats
        response = await client.get(
            "/api/b2b/billing/subscription",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["seat_count"] == 4
