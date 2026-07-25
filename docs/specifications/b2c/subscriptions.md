# SPEC-B2C-03: Subscriptions & Billing

**Status**: Active  
**Last Updated**: 2025-12-18

## 1. Overview
This specification outlines the requirements for the **Multi-Provider Subscription System**. The goal is to maximize market reach by supporting global and regional payment providers (Stripe, Razorpay, Xendit) while giving Platform Administrators granular control over pricing and plan configurations without code deployments.

## 2. Business Requirements

### 2.1 Multi-Provider Support
**Requirement**: The system MUST support multiple payment gateways simultaneously.
- **Stripe**: Primary global provider.
- **Razorpay**: Primary provider for India/SEA.
- **Xendit**: Primary provider for Indonesia/Philippines.
- **Selection**: The payment provider is determined at the **Plan Level**. (e.g., "Premium Tier" can be configured to use Stripe, while a specific "Regional Tier" uses Razorpay).

### 2.2 Dynamic Plan Management
**Requirement**: Platform Admins MUST be able to create and manage subscription plans via the Admin UI.
- **No Code Changes**: Creating a new price point or plan version should not require a code deployment or environment variable update.
- **Parameters**: Admins can define:
    - Display Name & Description
    - Price (Monthly/Yearly)
    - Quota Limits (Projects, Members, Storage)
    - Feature Flags (SSO, Audit Logs, etc.)
    - **Provider Configuration**: Select Provider and input external Plan/Price IDs.

### 2.3 Plan Scheduling & Versioning
**Requirement**: Pricing changes MUST be schedulable and versioned.
- **Effective Date**: Admins can set an `Effective From` date for a new plan version. The system must automatically start using this version for *new* subscriptions after that date.
- **Versioning**: Existing subscribers MUST remain on their original plan version (Legacy/Grandfathered status) unless they explicitly upgrade/downgrade.
- **Archiving**: Old plan versions can be archived to prevent new signups.

## 3. User Experience

### 3.1 End User (Subscriber)
- **Seamless Checkout**: Users simply select "Upgrade" and are directed to the secure checkout page of the configured provider.
- **Billing Portal**: Users can manage their subscription (Payment Methods, Invoices, Cancellation) via a self-serve portal.
- **Transparency**: Users can view their current Tier, usage against limits, and renewal date.

### 3.2 Platform Admin
- **Centralized Dashboard**: A single "Plans" page to view all active and archived plan versions.
- **Easy Configuration**: A wizard-style interface for creating new plan versions, validation of inputs (e.g., ensuring Price IDs are provided), and immediate visibility of active status.

## 4. Technical Constraints & Assumptions
- **One Active Subscription**: A Workspace can have only one active subscription at a time.
- **Provider Isolation**: A single subscription lifecycle stays within one provider. Switching providers (e.g. Stripe -> Razorpay) requires correct handling (cancellation on old -> new signup).
- **Security**: No sensitive payment credentials (PAN, CVV) are stored in the application database.

## 5. Reporting & Analytics
- **Standardized Data**: Regardless of the underlying provider, all subscription data (Status, Amount, Interval) is normalized in the database for consistent reporting.
- **Invoice History**: Users have access to a unified list of invoices, with direct links to provider-generated PDFs.
