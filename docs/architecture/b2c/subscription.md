# Architecture: B2C Subscription System

## 1. Overview
The B2C Subscription System manages the monetization lifecycle for personal workspace users. It is designed to be **provider-agnostic**, **database-driven**, and **flexible**, supporting multiple payment gateways (Stripe, Razorpay, Xendit) side-by-side.

## 2. Core Components

### 2.1 Database Schema
The system moves away from hardcoded plans to a dynamic, database-driven model.

- **`subscription_plans`**: Defines the product catalog.
    - `tier_key` (VARCHAR): Logical identifier (e.g., 'premium', 'ultimate') used by the application to gate features.
    - `provider_config` (JSONB): Stores provider-specific configurations (e.g., `{ "stripe": { "monthly_price_id": "...", "yearly_price_id": "..." }, "razorpay": { "plan_id": "..." } }`).
    - `limits` & `features` (JSONB): Defines quotas and capability flags.
    - `effective_from` (TIMESTAMP): Allows scheduling future plan versions.
    - `archived_at` (TIMESTAMP): Supports soft deletion of old plan versions.

- **`subscriptions`**: Links a user/workspace to a plan.
    - `plan_id` (UUID): FK to `subscription_plans`.
    - `provider` (VARCHAR): The payment provider handling this subscription (e.g., 'stripe', 'razorpay').
    - `provider_subscription_id` (VARCHAR): External ID for synchronization.

### 2.2 Application Logic
- **`SubscriptionService`**: The central orchestrator. It does **not** hardcode provider logic. Instead, it dynamically instantiates the correct `PaymentProvider` implementation based on the plan's `provider_config` or the subscription's `provider` field.
- **`PaymentProviderFactory`**: A factory pattern that returns instances of `StripeProvider`, `RazorpayProvider`, or `XenditProvider`.
- **`PaymentProvider` (Interface)**: Defines the contract for all providers (`create_checkout_session`, `cancel_subscription`, `get_invoice`, etc.).

### 2.3 Webhooks
Webhooks are essential for keeping the local database in sync with the payment provider. We use a **fan-out** or **dedicated endpoint** strategy.

- **Endpoints**:
    - `/api/b2c/billing/webhooks/stripe`: Verifies Stripe signatures.
    - `/api/b2c/billing/webhooks/razorpay`: Verifies Razorpay signatures.
    - `/api/b2c/billing/webhooks/xendit`: Verifies Xendit signatures.
- **Processing**: All webhooks eventually call standardized methods on `SubscriptionService` (e.g., `handle_checkout_completed`), passing normalized data.

## 3. Key Flows

### 3.1 Plan Creation (Platform Admin)
1.  Admin converts business requirements into a new Plan Version via Platform UI.
2.  Selects Payment Provider (e.g., Stripe) and enters Price IDs.
3.  Sets `effective_from` date (optional).
4.  System saves new row in `subscription_plans` with `provider_config`.

### 3.2 Checkout
1.  User selects a plan (Tier + Interval).
2.  Backend fetches the latest `active` plan version for that Tier.
3.  Reads `provider_config` to determine the Provider and Price ID.
4.  `SubscriptionService` requests `PaymentProviderFactory` for a provider instance.
5.  Calls `provider.create_checkout_session(...)`.
6.  Returns checkout URL to frontend.

### 3.3 Subscription Lifecycle
- **Activation**: Via Webhook (`checkout.session.completed` / `subscription.active`).
- **Cancellation**: Users cancel via App -> Backend calls `provider.cancel_subscription`.
- **Renewal**: Handled automatically by provider; Webhook updates local `current_period_end`.

## 4. Security & Compliance
- **PCI-DSS**: No raw card data is touched. Hosted Checkout pages and direct provider POSTs are used.
- **RLS (Row Level Security)**: Enforced at the database level. Users see only their own subscriptions/invoices. Platform Admins bypass RLS for management.
- **Audit**: All plan changes are tracked.

## 5. Scalability
- **New Providers**: Add a new class implementing `PaymentProvider` and register it in the Factory. No core logic changes needed.
- **Versioning**: Plans are versioned. Old subscriptions stay on old plan versions until migrated, ensuring grandfathering of prices is possible.
