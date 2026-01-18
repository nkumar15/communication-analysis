# Billing & Subscriptions (B2C)

## 1. Context
### Goal
Provide self-service billing for B2C users, allowing them to upgrade workspaces, view invoices, and redeem coupons.

### User Stories
- **As a User**, I want to upgrade my workspace to Premium so I can invite members.
- **As a Subscriber**, I want to download my invoice PDF for reimbursement.
- **As a User**, I want to apply a discount code during checkout.

### Key Business Rules
**1. Subscription Model**:
- **Tiers**: `Premium`, `Ultimate`.
- **Intervals**: Monthly, Yearly.

**2. Integrations**:
- **Stripe**: Primary provider for Checkout and Customer Portal.
- **Razorpay/Xendit**: Supported for regional payment processing.

**3. Checkouts**:
- Session-based (Stripe Checkout).
- Users can manage their own billing address and Tax IDs via the Profile API.

## 2. Architecture
### Data Flow
```mermaid
graph TD
    User -->|Checkout| API[BillingRouter]
    API -->|Create Session| Stripe
    Stripe -->|Customer Portal| User
    Stripe -->|Webhook| API
    API -->|Update| DB[(Subscriptions)]
```

### Database Schema
**Schema**: `b2c`
- `subscriptions`
- `invoices`
- `coupons`

## 3. API Reference
**Base Path**: `/api/b2c/billing`

| Method | Endpoint | Description | Role |
| :--- | :--- | :--- | :--- |
| **Subscription** | | | |
| `POST` | `/checkout` | Create Stripe Session | Owner |
| `GET` | `/subscription` | Get Status | Owner |
| `POST` | `/cancel` | Cancel Plan | Owner |
| `POST` | `/portal` | Open Stripe Portal | Owner |
| **Invoice** | | | |
| `GET` | `/invoices` | List History | Any |
| `GET` | `/invoices/{id}/download` | Get PDF | Any |
| **Coupons** | | | |
| `POST` | `/coupons/validate` | Check Code | Any |
| `GET` | `/coupons/available` | List Promos | Any |
| **Profile** | | | |
| `GET` | `/profile` | Get Tax/VAT Info | Any |
| `PATCH` | `/profile` | Update Tax/VAT | Any |

## 4. Dependencies
- **Internal**: `services.subscription_service`, `services.coupon_service`
- **External**: Stripe, Razorpay
