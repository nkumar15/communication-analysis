# B2B Platform System Specification

## 1. Overview
The **Platform System** is the super-admin interface used to manage the multi-tenant SaaS environment. It is completely isolated from the tenant data plane and has its own authentication, users, and roles.

**URL**: `http://localhost:3002` (Platform Portal)

---

## 2. Core Resources

### 2.1 Platform Tenant (Singleton)
Represents the SaaS provider itself. It is a singleton entity (only one exists).
- **Schema**: `platform`
- **Table**: `platform_tenant`
- **Attributes**: `firebase_tenant_id`, `name`, `support_email`

### 2.2 Platform User
Staff members who manage the platform. They are **not** members of any customer tenant.
- **Schema**: `platform`
- **Table**: `platform_users`
- **Attributes**: `email`, `firebase_uid`, `platform_role_id`

### 2.3 Customer Tenant (`Reference`)
The actual B2B organizations being managed.
- **Schema**: `b2b`
- **Table**: `tenants`

---

## 3. Roles & Permissions

The platform uses a Role-Based Access Control (RBAC) system within the `platform` schema.

### 3.1 Defined Roles

| Role Name | Slug | Description |
|-----------|------|-------------|
| **Platform Admin** | `platform_admin` | Superuser. Full access to all system functions and tenant management. |
| **Support Staff** | `support_staff` | *(Proposed)* Read-only access to tenant lists and impersonation capabilities. |
| **Billing Manager** | `billing_manager` | *(Proposed)* Access to subscription and payment data only. |

### 3.2 Permission Matrix

| Resource | Action | Platform Admin | Support | Billing |
|----------|--------|:--------------:|:-------:|:-------:|
| **Tenants** | `List / View` | ✅ | ✅ | ✅ |
| | `Onboard / Create` | ✅ | ❌ | ❌ |
| | `Deactivate` | ✅ | ❌ | ✅ |
| | `Soft Delete` | ✅ | ❌ | ❌ |
| | `Impersonate Admin` | ✅ | ✅ | ❌ |
| **Platform Users** | `Create / Manage` | ✅ | ❌ | ❌ |
| **System** | `View Audit Logs` | ✅ | ❌ | ✅ |

---

## 4. API Capabilities

The Platform API exposes the following high-level actions:

### Tenant Lifecycle
- **Onboard**: Create new B2B tenant, generate activation token, send invite.
- **Deactivate**: Instantly block access for a tenant (sets `is_active=False`).
- **Reactivate**: Restore access for a deactivated tenant.
- **Soft Delete**: Mark tenant for deletion (sets `deleted_at`).
- **Resend Invite**: Re-trigger the onboarding email for pending tenants.

### Support Actions
- **Impersonate**: Generate a short-lived session to log into the B2B portal as a specific tenant administrator.
- **Details View**: Deep inspection of tenant stats (user count, team count, auth provider status).

### Observability
- **Dashboard Stats**: Aggregate counts of Active vs Pending tenants and total users.
- **Audit Logging**: All write actions are recorded in `platform.platform_audit_log`.

---

## 5. Security Model

1.  **Isolation**: Platform data lives in the `platform` schema, physically separate from `b2b` data.
2.  **Authentication**: Uses a dedicated Firebase Tenant (`system-platform`) separate from customer auth.
3.  **Authorization**: Logic is enforced via `verify_platform_admin` middleware.
4.  **Audit**: Critical actions (impersonation, deletion) are immutable logged.
