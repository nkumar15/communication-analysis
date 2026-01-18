# B2B Foundation Module

## 1. Overview
The B2B Foundation module provides the core capabilities for Multi-Tenant SaaS. It handles tenant isolation, authentication, billing, and subscription management.

## 2. Architecture
This module follows a **Layered Architecture**:
- `routers/`: API endpoints
- `services/`: Business logic
- `models/`: Database entities
- `schemas/`: Pydantic models (DTOs)

## 3. Feature Documentation
Detailed technical documentation for each foundation feature can be found below:

### Core Identity & Access
- [Authentication](docs/authentication.md)
- [RBAC (Role Based Access Control)](docs/rbac.md)
- [Invitations & Member Management](docs/invitations.md)
- [Tenant Onboarding](docs/tenant-onboarding.md)
- [User Management](docs/user.md)

### Commercialization
- [Billing & Subscriptions](docs/billing.md)

### Platform
- [Dashboard](docs/dashboard.md)
- [Platform Integration](docs/b2b-platform.md)

## 4. Dependencies
- **Core**: `services.authentication`, `db.session`
- **External**: Stripe (Billing), Firebase (Auth)
