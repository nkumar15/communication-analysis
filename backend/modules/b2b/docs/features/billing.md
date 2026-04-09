# Billing & Subscriptions

> **Status**: ![Status](https://img.shields.io/badge/Status-Complete-green)

Enterprise-grade subscription management using Stripe.

## Quick Reference
- [Technical Spec](../technical/billing.md)
- [Billing Settings Page](../pages/settings_billing.md)
- [API Reference](../technical/api.md#billing)

## Overview
Handles all revenue-related operations including:
- **Subscription Lifecycle**: Upgrades, Downgrades, Cancellations.
- **Invoicing**: Automatic generation and email delivery.
- **Payment Methods**: Credit Card management via Stripe Customer Portal.

## Workflows

### 1. New Subscription
**Trigger**: Tenant Admin selects a plan.
**Process**:
1.  Backend creates Stripe Checkout Session.
2.  Admin completes payment on Stripe.
3.  Webhook updates `subscriptions` table.
**Output**: Active Subscription.

### 2. Invoice Generation
**Trigger**: Monthly cycle (Cron Job).
**Process**:
1.  System calculates usage (if metered) + base fee.
2.  Generates Invoice PDF.
3.  Emails to Tenant Owner.
**Output**: Sent Invoice.

## Implementation Checklist
- [x] Stripe Connect integration
- [x] Webhook handler implementation
- [x] `subscriptions` and `invoices` tables
- [x] Frontend Pricing Table component

## Design Decisions
| Decision | Rationale |
| :--- | :--- |
| **Stripe Checkout** | PCI compliance handled by Stripe. |
| **Async Webhooks** | Decouples payment processing from user request latency. |
| **Database Mirroring** | Local copies of core Stripe objects for fast queries/reporting. |
