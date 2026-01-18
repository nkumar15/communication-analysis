# Platform System Module

## 1. Overview
The Platform module provides the "Super-Admin" control plane for the entire SaaS. It is strictly isolated from customer data and used by internal staff (Support, Billing, Compliance) to manage Tenants (B2B) and Users (B2C).

## 2. Architecture
This module acts as the "God Mode" layer:
- **Middleware**: Dedicated `platform_auth` middleware ensures only staff with `platform:admin` claims can access these APIs.
- **Rls Bypass**: Services here explicitly set `app.is_platform_admin = true` to bypass Row Level Security.

## 3. Feature Documentation
Detailed technical documentation for platform capabilities:

### Administration
- [Identity & Access (IAM)](docs/iam.md): Staff management, Roles, and Invitations.
- [Tenant Management](docs/tenants.md): B2B Tenant onboarding, deactivation, and impersonation.
- [Billing & Plans](docs/billing.md): Unified billing, Plan definitions, and Coupon management.

### Security
- [Audit Logging](docs/audit.md): Immutable logs of all administrative actions.

## 4. Dependencies
- **Core**: `services.platform_service`, `db.session`
- **External**: Firebase (System Tenant)
