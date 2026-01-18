# Platform System (Super-Admin)

## 1. Context
### Goal
Provide a Super-Admin interface to manage the SaaS environment, isolated from customer data.

### User Stories
- **As a Platform Admin**, I want to onboard new tenants.
- **As Support Staff**, I want to impersonate a tenant admin to debug issues.
- **As a Billing Manager**, I want to deactivate non-paying tenants.

### Key Business Rules
**1. Isolation**:
- Platform data lives in `platform` schema.
- Built on a dedicated Firebase Tenant (`system-platform`).
- Distinct from B2B Customer data.

**2. Roles**:
- **Platform Admin**: Superuser.
- **Support Staff**: Read-only + Impersonation.

**3. Lifecycle**:
- **Deactivate**: Instant block (`is_active=False`).
- **Soft Delete**: Scheduled for removal.

## 2. Architecture
### Data Model
**Schema**: `platform`

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `platform_tenant` | Singleton config | `firebase_tenant_id`, `support_email` |
| `platform_users` | Staff members | `id`, `email`, `role` |
| `platform_audit_log` | Security audit | `action`, `actor_id`, `target_tenant_id` |

### Security
- **Middleware**: `verify_platform_admin`.
- **Audit**: All actions (Impersonation, Deletion) are logged immutably.

## 3. API Reference
**Base Path**: `/api/platform`

| Method | Endpoint | Description | Permission |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/platform/tenants` | Onboard Tenant | `platform:admin` |
| `POST` | `/api/platform/tenants/{id}/deactivate` | Block Access | `platform:admin` |
| `POST` | `/api/platform/tenants/{id}/impersonate` | Login as Customer | `platform:support` |
| `GET` | `/api/platform/stats` | System aggregates | `platform:read` |

## 4. Dependencies
- **Internal**: `services.platform_service`
- **External**: Firebase (System Tenant)
