# Billing Settings

## Overview

| Attribute | Details |
|-----------|---------|
| **Goal** | Manage tenant subscription, payment methods, and invoices |
| **Target Persona** | Tenant Owner (Alex) |
| **Permission** | `billing:read`, `billing:write` |

## Features/Widgets

| Widget | Description | Data Source |
|--------|-------------|-------------|
| **Current Plan** | Shows current tier, renewal date, and seat count | `subscriptions` table |
| **Usage Metrics** | Active seats vs Plan limit | `users` table count |
| **Payment Method** | Card details (Last 4) or Invoice Terms | Stripe API |
| **Invoice History** | List of past invoices with PDF download | `invoices` table |
| **Upgrade/Downgrade** | Pricing table to change plans | Config/Stripe |

## User Stories

- **As a Tenant Admin**, I want to see my next renewal date so that I can budget accordingly.
- **As a Tenant Admin**, I want to download past invoices for tax purposes.
- **As a Tenant Admin**, I want to upgrade my plan to add more seats.
- **As a Tenant Admin**, I want to update my credit card when it expires.

## UX Rules

- **Downgrade Warning**: Converting from Paid to Free must warn about feature loss.
- **Failed Payment**: Show "Payment Failed" banner if status is `past_due`.
- **Seat Limit**: Disable "Invite" button elsewhere if seat limit reached (and show upsell here).

## Demo Hook

> "Notice how the invoice history is automatically synced from Stripe. You don't need to manually generate PDF receipts."

## Technical Implementation

See [API Reference](../technical/api.md#billing)
