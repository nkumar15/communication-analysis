# B2B Billing & Subscription Specification

## Overview

The B2B billing system manages tenant-level subscriptions, invoice generation, payment processing, and support operations. It is designed to support both automated card payments (Stripe) and manual invoicing workflows.

## Subscription Tiers

### Starter (Free)
- **Base Price**: $0/month
- **Per-Seat Price**: $0/user
- **Features**: Basic SSO functionality
- **Payment Mode**: N/A (free)
- **Target**: Small teams evaluating the platform

### Professional
- **Base Price**: $50/month
- **Per-Seat Price**: $20/user/month
- **Features**: Advanced SSO, team management, basic audit logs
- **Payment Modes**: Card (Stripe) or Invoice
- **Billing Intervals**: Monthly or Yearly
- **Target**: Growing teams (5-50 users)

### Enterprise
- **Base Price**: $200/month
- **Per-Seat Price**: $50/user/month
- **Features**: All Professional features + advanced audit logs, custom SAML, priority support
- **Payment Modes**: Card (Stripe) or Invoice
- **Billing Intervals**: Monthly or Yearly
- **Target**: Large organizations (50+ users)

## Pricing Model

### Seat-Based Calculation
```
Total Monthly Cost = Base Price + (Active Seats × Per-Seat Price)
```

**Example (Professional tier, 10 active users):**
```
$50 + (10 × $20) = $250/month
```

### Seat Counting
1. **Active Seats**: Users with `is_active = true`.
2. **Recalculation**: Automated daily via Celery task.
3. **Billing Snapshot**: Seat count is frozen at billing period start.
4. **Mid-Period Changes**: New users added mid-period are billed in the next cycle.

### Yearly Billing
- **Discount**: 2 months free (pay for 10 months).
- **Calculation**: `(Monthly Cost × 10)`.
- **Payment**: Upfront for the year.

## Payment Modes

### Card (Stripe)
- **Processing**: Automated via Stripe Checkout.
- **Auto-Renewal**: Default.
- **Invoice Delivery**: Via Stripe email.

### Invoice (Billable)
- **Processing**: Manual payment (Wire/Check).
- **Approval**: Required to enabling this mode.
- **Terms**: Net 30 days.

## Support Operations 🆕

Platform admins have access to manual billing controls via the Dashboard.

### Manual Actions
1.  **Email Invoice**: Re-send invoice emails to tenant admins.
    *   *Trigger*: `POST /api/platform/billing/invoices/{id}/send`
2.  **Refund Invoice**: Initiate full or partial refunds for paid invoices.
    *   *Trigger*: `POST /api/platform/billing/invoices/{id}/refund`
    *   *Requirement*: Invoice status must be `PAID`.
3.  **Cancel Subscription**: Immediate or end-of-period cancellation.
    *   *Trigger*: `POST /api/platform/billing/subscriptions/{id}/cancel`

## Invoice Lifecycle

### Status Values
| Status | Description | Transitions |
|--------|-------------|-------------|
| `draft` | Created, not finalized | → `sent` |
| `sent` | Emailed to customer | → `paid`, `overdue`, `void` |
| `paid` | Payment successful | → `refunded` |
| `overdue` | Past due date | → `paid`, `void` |
| `void` | Invalidated | Terminal |
| `refunded` | Money returned | Terminal |

### Automated Flows
*   **Generation**: Monthly on the 1st via Celery beat.
*   **Payment Tracking**: 
    *   Stripe: Webhooks (`invoice.payment_succeeded`).
    *   Manual: Admin marks as paid.

## Coupon System

### B2B Coupons
*   **Scope**: Global (can be used by any tenant).
*   **Targeting**: Restricted via unique codes shared privately.
*   **Types**: Percentage off or Fixed amount.
*   **Application**: Applied at checkout or subscription creation.

## API Endpoints

### Tenant APIs
```
GET    /api/b2b/billing/subscription     # Get current sub
POST   /api/b2b/billing/checkout         # Create Stripe session
GET    /api/b2b/billing/invoices         # List invoices
GET    /api/b2b/billing/invoices/{id}    # Get PDF/Details
```

### Platform Admin APIs
```
GET    /api/platform/billing/profiles          # Search tenants
GET    /api/platform/billing/profiles/{id}     # Detail view
POST   /api/platform/billing/invoices/{id}/send   # Email invoice
POST   /api/platform/billing/invoices/{id}/refund # Refund
POST   /api/platform/billing/subscriptions/{id}/cancel
```

## Database Schema

### Key Tables
*   `b2b.subscriptions`: Active subscription state.
*   `b2b.invoices`: Generated invoices.
*   `b2b.coupons`: Discount codes.
*   `b2b.subscription_events`: Audit log of billing actions.

### Enums
*   `InvoiceStatus`: `draft`, `sent`, `paid`, `overdue`, `void`, `refunded`.
