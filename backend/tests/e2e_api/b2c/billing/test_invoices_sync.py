"""
Tests for B2C Invoice Sync Logic
"""
import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone
import time

from services.b2c.services.subscription_service import SubscriptionService
from services.b2c.models.subscription import Invoice, Subscription



@pytest.mark.asyncio
async def test_sync_invoice_with_periods(db_session):
    """Test syncing invoice with top-level period_start and period_end"""
    from core.rls import rls_service
    await rls_service.set_platform_admin_context(db_session)
    
    # Mock data
    period_start = int(time.time())
    period_end = period_start + 30*24*60*60
    
    invoice_data = {
        "id": "in_test_123",
        "subscription": "sub_test_123",
        "amount_due": 1000,
        "amount_paid": 1000,
        "currency": "usd",
        "status": "paid",
        "invoice_pdf": "https://example.com/invoice.pdf",
        "hosted_invoice_url": "https://example.com/invoice",
        "created": period_start,
        "period_start": period_start,
        "period_end": period_end,
        "status_transitions": {
            "paid_at": period_end
        }
    }
    
    service = SubscriptionService(db_session)
    
    # Sync
    invoice = await service.sync_invoice(invoice_data)
    
    assert invoice.provider_invoice_id == "in_test_123"
    assert invoice.billing_period_start.replace(tzinfo=timezone.utc) == datetime.fromtimestamp(period_start, tz=timezone.utc)
    assert invoice.billing_period_end.replace(tzinfo=timezone.utc) == datetime.fromtimestamp(period_end, tz=timezone.utc)


@pytest.mark.asyncio
async def test_sync_invoice_fallback_to_lines(db_session):
    """Test syncing invoice extracting period from lines"""
    from core.rls import rls_service
    await rls_service.set_platform_admin_context(db_session)
    
    period_start = int(time.time())
    period_end = period_start + 30*24*60*60
    
    invoice_data = {
        "id": "in_test_lines",
        "subscription": "sub_test_123", # Assuming no sub lookup effectively used if not found or irrelevant for fields
        "amount_due": 1000,
        "currency": "usd",
        "status": "paid",
        # No top-level period
        "lines": {
            "data": [
                {
                    "period": {
                        "start": period_start,
                        "end": period_end
                    }
                }
            ]
        }
    }
    
    service = SubscriptionService(db_session)
    invoice = await service.sync_invoice(invoice_data)
    
    assert invoice.provider_invoice_id == "in_test_lines"
    assert invoice.billing_period_start.replace(tzinfo=timezone.utc) == datetime.fromtimestamp(period_start, tz=timezone.utc)
    assert invoice.billing_period_end.replace(tzinfo=timezone.utc) == datetime.fromtimestamp(period_end, tz=timezone.utc)
