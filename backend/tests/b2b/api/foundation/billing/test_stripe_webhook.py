"""
API Layer: Stripe Webhook Endpoint Tests

Tests POST /api/b2b/billing/webhooks/stripe for:
  - Signature verification (400 on bad sig, 200 on valid)
  - checkout.session.completed delegates to subscription service
  - invoice.paid / invoice.payment_failed handled without 500
  - Unknown event types return 200 (ignored, not errored)

Mocks:
  - stripe.Webhook.construct_event   → bypasses Stripe SDK signature check
  - SubscriptionService.handle_checkout_completed → avoids real Stripe provider calls
  - InvoiceService.sync_stripe_invoice → avoids DB invoice dependencies

Business logic (plugin activation, DB writes) is covered in:
  tests/b2b/services/foundation/billing/test_subscription_checkout.py
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
from fastapi import status

pytestmark = pytest.mark.asyncio

WEBHOOK_URL = "/api/b2b/billing/webhooks/stripe"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _stripe_event(event_type: str, tenant_id: str, tier: str = "enterprise") -> dict:
    """Build a fake Stripe event object."""
    return {
        "id": f"evt_{uuid4().hex[:8]}",
        "type": event_type,
        "data": {
            "object": {
                "id": f"cs_{uuid4().hex[:8]}",
                "customer": f"cus_{uuid4().hex[:8]}",
                "subscription": f"sub_{uuid4().hex[:8]}",
                "metadata": {
                    "tenant_id": tenant_id,
                    "tier": tier,
                    "billing_interval": "monthly",
                    "seat_count": "5",
                },
            }
        },
    }


def _invoice_event(event_type: str, tenant_id: str) -> dict:
    """Build a fake Stripe invoice event."""
    return {
        "id": f"evt_{uuid4().hex[:8]}",
        "type": event_type,
        "data": {
            "object": {
                "id": f"in_{uuid4().hex[:8]}",
                "subscription": f"sub_{uuid4().hex[:8]}",
                "metadata": {"tenant_id": tenant_id},
                "status": "paid" if event_type == "invoice.paid" else "open",
                "amount_due": 500000,
                "currency": "usd",
            }
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Signature Verification
# ─────────────────────────────────────────────────────────────────────────────

class TestWebhookSignatureVerification:
    """Stripe signature header must be validated before processing any event."""

    async def test_invalid_signature_returns_400(self, api_client):
        """Tampered or missing signature must be rejected with 400."""
        import stripe

        with patch.object(
            stripe.Webhook,
            "construct_event",
            side_effect=stripe.error.SignatureVerificationError("bad sig", "sig_header"),
        ):
            response = await api_client.post(
                WEBHOOK_URL,
                content=b'{"type":"checkout.session.completed"}',
                headers={"stripe-signature": "bad_sig"},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_invalid_payload_returns_400(self, api_client):
        """Malformed payload (not JSON) must be rejected with 400."""
        import stripe

        with patch.object(
            stripe.Webhook,
            "construct_event",
            side_effect=ValueError("Invalid payload"),
        ):
            response = await api_client.post(
                WEBHOOK_URL,
                content=b"not-json",
                headers={"stripe-signature": "some_sig"},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────────────────────────────────────────────────────────
# checkout.session.completed
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckoutSessionCompleted:
    """Webhook handler must delegate checkout events to the subscription service."""

    async def test_checkout_completed_returns_200(self, api_client, b2b_test_setup):
        """
        Valid checkout.session.completed event must return 200.
        The subscription service handles the business logic.
        """
        import stripe

        tenant_id = str(b2b_test_setup["tenant_id"])
        event = _stripe_event("checkout.session.completed", tenant_id)

        mock_subscription = MagicMock()
        mock_subscription.id = uuid4()
        mock_subscription.tier = "enterprise"

        with (
            patch.object(stripe.Webhook, "construct_event", return_value=event),
            patch(
                "modules.b2b.services.subscription_service.SubscriptionService.handle_checkout_completed",
                new_callable=AsyncMock,
                return_value=mock_subscription,
            ),
        ):
            response = await api_client.post(
                WEBHOOK_URL,
                content=b"fake-stripe-payload",
                headers={"stripe-signature": "t=1,v1=abc"},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "success"

    async def test_checkout_completed_calls_handle_checkout_once(
        self, api_client, b2b_test_setup
    ):
        """
        Webhook handler must call handle_checkout_completed exactly once
        with the event's data object.
        """
        import stripe

        tenant_id = str(b2b_test_setup["tenant_id"])
        event = _stripe_event("checkout.session.completed", tenant_id)
        session_data = event["data"]["object"]

        mock_subscription = MagicMock()
        mock_subscription.id = uuid4()
        mock_subscription.tier = "enterprise"

        with (
            patch.object(stripe.Webhook, "construct_event", return_value=event),
            patch(
                "modules.b2b.services.subscription_service.SubscriptionService.handle_checkout_completed",
                new_callable=AsyncMock,
                return_value=mock_subscription,
            ) as mock_handle,
        ):
            await api_client.post(
                WEBHOOK_URL,
                content=b"fake-payload",
                headers={"stripe-signature": "t=1,v1=abc"},
            )

        mock_handle.assert_called_once_with(session_data)

    async def test_checkout_service_exception_returns_500(
        self, api_client, b2b_test_setup
    ):
        """
        If handle_checkout_completed raises, the webhook must return 500
        (Stripe will retry).
        """
        import stripe

        tenant_id = str(b2b_test_setup["tenant_id"])
        event = _stripe_event("checkout.session.completed", tenant_id)

        with (
            patch.object(stripe.Webhook, "construct_event", return_value=event),
            patch(
                "modules.b2b.services.subscription_service.SubscriptionService.handle_checkout_completed",
                new_callable=AsyncMock,
                side_effect=RuntimeError("DB connection lost"),
            ),
        ):
            response = await api_client.post(
                WEBHOOK_URL,
                content=b"fake-payload",
                headers={"stripe-signature": "t=1,v1=abc"},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ─────────────────────────────────────────────────────────────────────────────
# invoice.paid
# ─────────────────────────────────────────────────────────────────────────────

class TestInvoicePaid:
    """invoice.paid must sync the Stripe invoice without touching plugins."""

    async def test_invoice_paid_returns_200(self, api_client, b2b_test_setup):
        """Valid invoice.paid event returns 200."""
        import stripe

        tenant_id = str(b2b_test_setup["tenant_id"])
        event = _invoice_event("invoice.paid", tenant_id)

        mock_invoice = MagicMock()
        mock_invoice.id = uuid4()

        with (
            patch.object(stripe.Webhook, "construct_event", return_value=event),
            patch(
                "modules.b2b.services.invoice_service.InvoiceService.sync_stripe_invoice",
                new_callable=AsyncMock,
                return_value=mock_invoice,
            ),
        ):
            response = await api_client.post(
                WEBHOOK_URL,
                content=b"fake-payload",
                headers={"stripe-signature": "t=1,v1=abc"},
            )

        assert response.status_code == status.HTTP_200_OK

    async def test_invoice_paid_race_condition_deferred(
        self, api_client, b2b_test_setup
    ):
        """
        If invoice arrives before checkout (subscription not found),
        handler must return 200 with deferred status so Stripe retries later.
        """
        import stripe

        tenant_id = str(b2b_test_setup["tenant_id"])
        event = _invoice_event("invoice.paid", tenant_id)

        with (
            patch.object(stripe.Webhook, "construct_event", return_value=event),
            patch(
                "modules.b2b.services.invoice_service.InvoiceService.sync_stripe_invoice",
                new_callable=AsyncMock,
                side_effect=ValueError("Subscription not found"),
            ),
        ):
            response = await api_client.post(
                WEBHOOK_URL,
                content=b"fake-payload",
                headers={"stripe-signature": "t=1,v1=abc"},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "deferred"


# ─────────────────────────────────────────────────────────────────────────────
# invoice.payment_failed
# ─────────────────────────────────────────────────────────────────────────────

class TestInvoicePaymentFailed:
    """invoice.payment_failed must sync invoice and queue a payment failure alert task."""

    async def test_payment_failed_returns_200(self, api_client, b2b_test_setup):
        """Valid invoice.payment_failed event returns 200."""
        import stripe

        tenant_id = str(b2b_test_setup["tenant_id"])
        event = _invoice_event("invoice.payment_failed", tenant_id)

        mock_invoice = MagicMock()
        mock_invoice.id = uuid4()
        mock_invoice.tenant_id = b2b_test_setup["tenant_id"]

        with (
            patch.object(stripe.Webhook, "construct_event", return_value=event),
            patch(
                "modules.b2b.services.invoice_service.InvoiceService.sync_stripe_invoice",
                new_callable=AsyncMock,
                return_value=mock_invoice,
            ),
            patch(
                "modules.b2b.tasks.billing.send_payment_failure_alert.delay"
            ) as mock_task,
        ):
            response = await api_client.post(
                WEBHOOK_URL,
                content=b"fake-payload",
                headers={"stripe-signature": "t=1,v1=abc"},
            )

        assert response.status_code == status.HTTP_200_OK
        mock_task.assert_called_once_with(
            tenant_id=str(mock_invoice.tenant_id),
            invoice_id=str(mock_invoice.id),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Unknown / unhandled event types
# ─────────────────────────────────────────────────────────────────────────────

class TestUnknownEventTypes:
    """Unknown event types must be silently accepted (200) and not raise."""

    async def test_unknown_event_returns_200(self, api_client, b2b_test_setup):
        """Unhandled event type must return 200 without error."""
        import stripe

        tenant_id = str(b2b_test_setup["tenant_id"])
        event = _stripe_event("customer.created", tenant_id)

        with patch.object(stripe.Webhook, "construct_event", return_value=event):
            response = await api_client.post(
                WEBHOOK_URL,
                content=b"fake-payload",
                headers={"stripe-signature": "t=1,v1=abc"},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "success"
