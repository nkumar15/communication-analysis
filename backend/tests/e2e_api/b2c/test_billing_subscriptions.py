"""
E2E Tests for B2C Billing - Subscriptions
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from datetime import datetime, timedelta

from services.b2c.models.subscription import Subscription


@pytest.mark.asyncio
async def test_create_checkout_session(api_client: AsyncClient, b2c_billing_user, mock_stripe_provider):
    """Test creating a Stripe checkout session"""
    
    with patch('services.b2c.services.subscription_service.PaymentProviderFactory.create', return_value=mock_stripe_provider), \
         patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        
        response = await api_client.post(
            "/api/b2c/billing/checkout",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"},
            json={
                "workspace_id": str(b2c_billing_user["workspace"].id),
                "tier": "premium",
                "billing_interval": "monthly",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "checkout_session_id" in data
    assert "checkout_url" in data
    assert data["checkout_url"].startswith("https://checkout.stripe.com")


@pytest.mark.asyncio
async def test_create_checkout_with_coupon(api_client: AsyncClient, b2c_billing_user, active_coupon, mock_stripe_provider):
    """Test checkout with valid coupon code"""
    
    with patch('services.b2c.services.subscription_service.PaymentProviderFactory.create', return_value=mock_stripe_provider), \
         patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        
        response = await api_client.post(
            "/api/b2c/billing/checkout",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"},
            json={
                "workspace_id": str(b2c_billing_user["workspace"].id),
                "tier": "premium",
                "billing_interval": "monthly",
                "coupon_code": active_coupon.code
            }
        )
    
    assert response.status_code == 200
    # Coupon should be validated but checkout should still succeed even if invalid


@pytest.mark.asyncio
async def test_checkout_invalid_tier(api_client: AsyncClient, b2c_billing_user):
    """Test checkout rejects invalid tier"""
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.post(
            "/api/b2c/billing/checkout",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"},
            json={
                "workspace_id": str(b2c_billing_user["workspace"].id),
                "tier": "invalid_tier",
                "billing_interval": "monthly"
            }
        )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_subscription_free_tier(api_client: AsyncClient, b2c_billing_user):
    """Test getting subscription returns 404 for free tier"""
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.get(
            f"/api/b2c/billing/subscription?workspace_id={b2c_billing_user['workspace'].id}",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"}
        )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_subscription_premium(api_client: AsyncClient, b2c_billing_user, premium_subscription):
    """Test getting active premium subscription"""
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.get(
            f"/api/b2c/billing/subscription?workspace_id={b2c_billing_user['workspace'].id}",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "premium"
    assert data["status"] == "active"
    assert data["billing_interval"] == "monthly"
    assert data["amount_cents"] == 1900


@pytest.mark.asyncio
async def test_cancel_subscription_at_period_end(api_client: AsyncClient, b2c_billing_user, premium_subscription, mock_stripe_provider, db_session):
    """Test canceling subscription at period end"""
    
    with patch('services.b2c.services.subscription_service.PaymentProviderFactory.create', return_value=mock_stripe_provider), \
         patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        
        response = await api_client.post(
            f"/api/b2c/billing/subscription/cancel?workspace_id={b2c_billing_user['workspace'].id}&immediate=false",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"  # Still active until period end
    assert data["cancel_at_period_end"] == True


@pytest.mark.asyncio
async def test_cancel_subscription_immediately(api_client: AsyncClient, b2c_billing_user, premium_subscription, mock_stripe_provider):
    """Test immediate subscription cancellation"""
    
    with patch('services.b2c.services.subscription_service.PaymentProviderFactory.create', return_value=mock_stripe_provider), \
         patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        
        response = await api_client.post(
            f"/api/b2c/billing/subscription/cancel?workspace_id={b2c_billing_user['workspace'].id}&immediate=true",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "canceled"


@pytest.mark.asyncio
async def test_customer_portal_session(api_client: AsyncClient, b2c_billing_user, premium_subscription, mock_stripe_provider):
    """Test creating customer portal session"""
    
    with patch('services.b2c.services.subscription_service.PaymentProviderFactory.create', return_value=mock_stripe_provider), \
         patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        
        response = await api_client.post(
            "/api/b2c/billing/portal",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"},
            json={"return_url": "https://example.com/billing"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "portal_url" in data
    assert data["portal_url"].startswith("https://billing.stripe.com")


@pytest.mark.asyncio
async def test_list_invoices_empty(api_client: AsyncClient, b2c_billing_user):
    """Test listing invoices returns empty for new user"""
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.get(
            "/api/b2c/billing/invoices",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "invoices" in data
    assert len(data["invoices"]) == 0


@pytest.mark.asyncio
async def test_download_invoice(api_client: AsyncClient, b2c_billing_user, premium_subscription, db_session):
    """Test downloading invoice PDF"""
    from services.b2c.models.subscription import Invoice
    
    # Create test invoice
    invoice = Invoice(
        subscription_id=premium_subscription.id,
        user_id=b2c_billing_user["user"].id,
        provider_invoice_id=f"in_{uuid4().hex[:12]}",
        amount_due=1900,
        amount_paid=1900,
        currency="USD",
        status="paid",
        invoice_pdf_url="https://invoice.stripe.com/test.pdf",
        invoice_date=datetime.now()
    )
    db_session.add(invoice)
    await db_session.commit()
    await db_session.refresh(invoice)
    
    with patch('services.b2c.middleware.b2c_auth.firebase_auth_service.verify_id_token', new=AsyncMock(return_value=b2c_billing_user["mock_token_data"])):
        response = await api_client.get(
            f"/api/b2c/billing/invoices/{invoice.id}/download",
            headers={"Authorization": f"Bearer {b2c_billing_user['auth_token']}"},
            follow_redirects=False
        )
    
    # Should redirect to Stripe PDF
    assert response.status_code == 307
    assert response.headers["location"] == invoice.invoice_pdf_url
