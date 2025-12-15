# SPEC-B2C-03: Subscriptions & Billing

**Status**: Active  
**Last Updated**: 2025-12-15

## 1. Overview

The subscription system provides monetization for the B2C SaaS platform. It is built using **Async SQLAlchemy** and integrates with **Stripe** (and adaptable for others) via a robust abstraction layer.

Subscriptions are strictly tied to **Workspaces**. Each workspace has exactly one active subscription (which defaults to the Free tier). Feature access and quotas are enforced based on the workspace's current subscription tier.

## 2. Architecture & Components

The system is composed of the following key components:

### 2.1 Core Services (`services.b2c.services`)

- **`SubscriptionService`**: main async service handling subscription lifecycle, checking out, cancellations, and portal sessions.
- **`CouponService`**: async service for validating coupon codes, tracking redemptions, and managing discounts.

### 2.2 Billing Router (`services.b2c.routers.billing`)

Exposes REST endpoints for the frontend:
- `POST /checkout`: Creates a Stripe Checkout Session.
- `POST /portal`: Creates a Stripe Customer Portal session.
- `GET /subscription`: Retrieves current subscription details.
- `POST /cancel`: Cancels subscription (immediately or at period end).
- `GET /invoices`: List past invoices.
- `GET /invoices/{id}`: Get invoice details (PDF download).
- `POST /webhooks/{provider}`: Handles asynchronous events from payment providers.

### 2.3 Data Models (`services.b2c.models.subscription`)

- **`Subscription`**: The central record linking a `Workspace` to a payment plan.
- **`Invoice`**: Records of payments made (synced from provider).
- **`Coupon`** & **`CouponRedemption`**: Promotional system.
- **`PaymentMethod`**: Stored payment instruments (though Stripe Checkout manages this largely on their side).

### 2.4 Row Level Security (RLS)

PostgreSQL RLS is strictly enforced.
- **Subscriptions/Invoices**: Users can only view/manage records linked to their Own Workspaces (via `workspace_id` ownership checks or direct `user_id` match).
- **Coupons**: Public reference data (read-only for users), strictly managed by system/admin for creation.
- **Webhooks**: Run with a service role (bypassing RLS) to ensure data consistency during background processing.

## 3. Subscription Tiers

| Tier | Price | Limits | Key Features |
|------|-------|--------|--------------|
| **Free** | $0/mo | 1 Workspace, 5 Projects, 100MB | Basic Personal Use |
| **Premium** | $12/mo | 3 Team Workspaces, Unlimited Projects, 10GB | Collaboration, Priority Support |
| **Ultimate** | $49/mo | Unlimited Workspaces/Members, 100GB | SSO, Audit Logs, Dedicated Support |

## 4. Data Model

### 4.1 Database Schema (Simplified)

```sql
-- Subscriptions
CREATE TABLE b2c.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID UNIQUE REFERENCES b2c.workspaces(id),
    user_id UUID REFERENCES b2c.users(id),
    
    provider VARCHAR(50) DEFAULT 'stripe',
    provider_subscription_id VARCHAR(255) UNIQUE,
    provider_customer_id VARCHAR(255),
    
    tier VARCHAR(50) DEFAULT 'free',
    status VARCHAR(50) DEFAULT 'active',
    
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Invoices
CREATE TABLE b2c.invoices (
    id UUID PRIMARY KEY,
    subscription_id UUID REFERENCES b2c.subscriptions(id),
    amount_paid INTEGER,
    status VARCHAR(50),
    invoice_pdf_url TEXT
);
```

**Note on Timezones**: All timestamps are stored as `TIMESTAMP WITH TIME ZONE` (UTC) to prevent timezone-related bugs during billing cycles.

## 5. Implementation Details

### 5.1 Async Service Layer

All database interactions use `sqlalchemy.ext.asyncio`.

```python
class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_checkout_session(self, user, workspace, tier, interval, ...):
        # 1. Validation (Invalid tier, existing sub)
        # 2. Get/Create Stripe Customer
        # 3. Create Stripe Checkout Session
        # 4. Return session URL
```

### 5.2 Checkout Flow

We use **Stripe Checkout** (hosted page) for security and simplicity.

1. **Frontend**: User selects plan -> calls `POST /api/b2c/billing/checkout`.
2. **Backend**: 
   - Validates request.
   - Creates `stripe.onboarding.Session` or `stripe.checkout.Session`.
   - Returns `checkout_url`.
3. **Frontend**: Redirects user to Stripe.
4. **Stripe**: User enters payment info -> Redirects to `success_url` on success.
5. **Webhook**: Stripe sends `checkout.session.completed` -> Backend provisions subscription.

### 5.3 Webhook Handling

Webhooks are the source of truth for subscription status.

- `checkout.session.completed`: Provision new subscription. update workspace quota.
- `customer.subscription.updated`: Handle renewals, plan changes.
- `customer.subscription.deleted`: Downgrade workspace to Free tier.
- `invoice.payment_failed`: Notify user, update status to `past_due`.

### 5.4 Coupon System

Implemented via `CouponService`.

- **Validation**: Checks code existence, expiration dates, max redemptions, and tier applicability.
- **Redemption**: 
  - API: `POST /api/b2c/billing/coupons/validate` returns discount details.
  - Checkout: Coupon code passed to Stripe Checkout Session.
  - Webhook: When subscription is created with discount, `CouponRedemption` record is created locally.

### 5.5 Invoice Management

Invoices are generated by the Payment Provider (Stripe) and synced to the local `invoices` table via webhooks (`invoice.payment_succeeded`, `invoice.payment_failed`).

- **History**: Users can list their complete invoice history via `GET /invoices`.
- **PDFs**: The API returns a `hosted_invoice_url` (view online) and `invoice_pdf_url` (direct download) generated by Stripe.
- **Failures**: Failed payments generate an open invoice with `payment_failed` status, triggering a grace period or immediate downgrade logic.

## 6. Access Control & RLS

Subscription data is sensitive.

- **RLS Policies**: prevent Cross-Tenant data access.
- **API Layer**: `get_subscription` enforces that `current_user` owns the `workspace`.
- **Portal**: Stripe Customer Portal is generated via a short-lived link, only accessible to the authenticated workspace owner.

## 7. Future Considerations

- **Proration**: Currently handled by Stripe/Provider default logic.
- **Multi-Currency**: Schema supports it (`currency` column), but currently defaults to USD.
- **Usage-Based Billing**: Foundations exist (events table), but metered billing is not yet implemented.
