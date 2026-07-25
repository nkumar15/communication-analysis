"""
E2E Tests for B2B Billing Portal
"""
import pytest
from unittest.mock import patch
from modules.b2b.models import Subscription, SubscriptionTier, PaymentMode, SubscriptionStatus

pytestmark = pytest.mark.asyncio

class TestBillingPortal:
    """Test billing portal endpoints"""

    async def test_create_portal_session_success(
        self,
        api_client,
        db_session,
        b2b_tenant,
        b2b_tenant_owner_token
    ):
        """Test creating a portal session successfully"""
        from core.db.rls import rls_service
        await rls_service.set_tenant_context(db_session, b2b_tenant.id)
        
        # Create subscription with customer_id
        subscription = Subscription(
            tenant_id=b2b_tenant.id,
            tier=SubscriptionTier.PROFESSIONAL.value,
            payment_mode=PaymentMode.CARD.value,
            status=SubscriptionStatus.ACTIVE.value,
            seat_count=5,
            provider_customer_id="cus_test123", # Required for portal
            total_amount_cents=5000
        )
        db_session.add(subscription)
        await db_session.commit()
        
        # Mock the service method to avoid Stripe calls
        with patch("modules.b2b.services.subscription_service.SubscriptionService.create_portal_session") as mock_create:
            mock_create.return_value = "https://billing.stripe.com/p/session/test_123"
            
            response = await api_client.post(
                "/api/b2b/billing/portal",
                headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"},
                json={"return_url": "http://localhost:3000/app/billing"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["url"] == "https://billing.stripe.com/p/session/test_123"
            
            # Verify mock was called with correct args
            mock_create.assert_called_once()
            
            # Check kwargs/args carefully
            call_kwargs = mock_create.call_args.kwargs
            if not call_kwargs:
                # Fallback if called positionally (unlikely given router code)
                args = mock_create.call_args[0]
                assert str(args[0]) == str(b2b_tenant.id)
            else:
                assert str(call_kwargs['tenant_id']) == str(b2b_tenant.id)

    async def test_create_portal_no_subscription(
        self,
        api_client,
        b2b_tenant,
        b2b_tenant_owner_token
    ):
        """Test creating portal session without a subscription (should fail)"""
        # No subscription created via fixture/setup
        
        # Mock valid service just in case, but logic should fail before reaching provider if correct
        # Actually our service logic checks for sub/customer ID before calling provider
        
        response = await api_client.post(
            "/api/b2b/billing/portal",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"},
            json={"return_url": "http://localhost:3000/app/billing"}
        )
        
        # Expect 400 or 500 depending on how implementation handles it.
        # Router catches ValueError -> 400
        # Service raises ValueError if "No billing account found"
        assert response.status_code == 400
        assert "upgrade" in response.json()["detail"].lower()

    async def test_create_portal_unsafe_return_url(
        self,
        api_client,
        db_session,
        b2b_tenant,
        b2b_tenant_owner_token
    ):
        """Test that unsafe return URLs are ignored/sanitized"""
        from core.db.rls import rls_service
        from core.config import settings
        
        await rls_service.set_tenant_context(db_session, b2b_tenant.id)
        
        # Create valid sub
        subscription = Subscription(
            tenant_id=b2b_tenant.id,
            tier=SubscriptionTier.PROFESSIONAL.value,
            provider_customer_id="cus_test123",
            total_amount_cents=5000
        )
        db_session.add(subscription)
        await db_session.commit()
        
        with patch("modules.b2b.services.subscription_service.SubscriptionService.create_portal_session") as mock_create:
            mock_create.return_value = "https://example.com"
            
            response = await api_client.post(
                "/api/b2b/billing/portal",
                headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"},
                json={"return_url": "https://evil.com/phishing"}
            )
            
            assert response.status_code == 200
            
            # Check what was passed to service
            # Router passes as keyword args
            call_kwargs = mock_create.call_args.kwargs
            if call_kwargs:
                passed_url = call_kwargs['return_url']
            else:
                # Fallback to positional
                args = mock_create.call_args[0]
                passed_url = args[1]
            
            assert passed_url != "https://evil.com/phishing"
            assert passed_url.startswith(settings.frontend_url)
