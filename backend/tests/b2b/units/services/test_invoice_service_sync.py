import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4
from modules.b2b.services.invoice_service import InvoiceService
from modules.b2b.models import Subscription, Invoice

@pytest.mark.asyncio
async def test_sync_stripe_invoice_with_missing_dates():
    # Mock DB Session
    db = AsyncMock()
    
    # Mock Subscription
    subscription = Subscription(
        id=uuid4(),
        tenant_id=uuid4(),
        provider_subscription_id="sub_123",
        seat_count=5,
        base_price_cents=1000,
        per_seat_price_cents=200,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc)
    )
    
    # Mock Select Execution
    # First call: Select Subscription
    # Second call: Select Invoice (returns None)
    mock_result_sub = MagicMock()
    mock_result_sub.scalar_one_or_none.return_value = subscription
    
    mock_result_inv = MagicMock()
    mock_result_inv.scalar_one_or_none.return_value = None
    
    # Setup execute side effects:
    # 1st call: set_platform_admin_context (SET LOCAL ...) - returns irrelevant MagicMock
    # 2nd call: Select Subscription
    # 3rd call: Select Invoice (returns None)
    mock_set_context = MagicMock()
    db.execute.side_effect = [mock_set_context, mock_result_sub, mock_result_inv]

    service = InvoiceService(db)
    
    # Payload MISSING period_start/end and lines
    payload = {
        "id": "in_123",
        "subscription": "sub_123",
        "amount_due": 5000,
        "currency": "usd",
        "status": "paid",
        "created": 1700000000
    }
    
    # Execute
    invoice = await service.sync_stripe_invoice(payload)
    
    # Verify Fallbacks
    # Should use 'created' timestamp for start/end if sub defaults fail or logic prefers invoice date
    # Actually code prefers sub dates if available.
    
    assert invoice.invoice_number == "STRIPE-in_123"
    assert invoice.billing_period_start is not None
    assert invoice.billing_period_end is not None
    # Check that it didn't crash
