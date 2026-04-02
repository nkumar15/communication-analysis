# B2B Foundation Module

## 1. Overview
The B2B Foundation module provides the core capabilities for Multi-Tenant SaaS. It handles tenant isolation, authentication, billing, and subscription management.

## 2. Architecture
This module follows a **Layered Architecture**:
- `routers/`: API endpoints
- `services/`: Business logic
- `models/`: Database entities
- `schemas/`: Pydantic models (DTOs)

## 3. Documentation

| Document | Description |
|----------|-------------|
| [Product Overview](docs/README.md) | Personas, Navigation, and Feature Specs |
| [Page Specifications](docs/pages/) | Detailed UI Specs (Dashboard, Billing, Team) |
| [Technical Reference](docs/technical/) | API, Schema, Architecture |

### Key Features
- [Authentication](docs/features/authentication.md)
- [RBAC & Permissions](docs/features/rbac.md)
- [Billing & Subscriptions](docs/features/billing.md)
- [Team Management](docs/features/team_management.md)

### Domain Features
Specialized vertical solutions built on the B2B foundation:

- [Bank Surveillance](../domains/b2b/bank_surveillance/docs/README.md) - Enterprise communication surveillance platform

## 4. Dependencies
- **Core**: `services.authentication`, `db.session`
- **External**: Stripe (Billing), Firebase (Auth)
