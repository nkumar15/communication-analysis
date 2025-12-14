# Growth Workflows: Onboarding & Invitations

**Audience:** Product Managers, Frontend Developers, Backend Engineers

This document visualizes the core growth workflows: **Tenant Activation** (Onboarding), **User Invitation**, and **Platform Administration**.

For lower-level details on how requests are secured, see:
-   [Authentication Architecture](./authentication.md) - Request lifecycle & Mobile Auth
-   [Multi-Tenant Isolation](./multi-tenant-isolation.md) - RLS Mechanics

---
## 1. Tenant Activation Flow 🚀

How a "Pending" tenant becomes "Active" via the owner's first login.

> **Technical Note**: For the detailed cryptographic handshake and token exchange during activation, please refer to the **[Authentication Architecture](./authentication.md#4-tenant-activation--onboarding-flow)** document.

### High-Level Process

1.  **Email Received**: Owner clicks unique activation link.
2.  **Validation**: Backend validates the signed token.
3.  **Authentication**: Owner logs in via SSO (proving they own the email).
4.  **Provisioning**: 
    *   Tenant status flips `pending` -> `active`.
    *   Owner user is created in Postgres.
    *   Initial "Default Team" is assigned.

### Key API Endpoints
*   `GET /api/public/activate/validate/{token}`: Public validation.
*   `POST /api/activate/complete`: Authenticated finalization step.

---

## 2. User Invitation Flow 📩

How an existing tenant admin invites a new member.

### Process Overview

1.  **Invite Sent**: Admin creates invitation via API.
2.  **Invite Clicked**: User validates token.
3.  **Acceptance**: User clicks "Join Team" (Requires SSO Login).
4.  **Creation**: User record created and assigned to Role/Team.

### Security Model (RLS Bypass)
Since the `GET /invitations/{token}` endpoint is public (no user context yet), it uses a special **RLS Bypass** pattern:
1.  Router temporarily grants **Platform Admin** context (`app.is_platform_admin=true`).
2.  Looks up token globally across all tenants.
3.  Once found, immediately **scopes down** to that specific tenant (`set_tenant_context`).

---

## 3. Platform Admin Flows ⚡

Super-admin capabilities for managing the system.

### Platform Mermaid Diagram

```mermaid
sequenceDiagram
    participant Admin as Platform Admin (React)
    participant BE as Backend API
    participant DB as Database
    participant Firebase as Firebase Auth

    Note over Admin: 1. Login Flow
    Admin->>BE: GET /api/platform/config
    BE->>DB: SELECT system tenant
    BE-->>Admin: 200 {firebase_tenant_id, oidc_provider_id}
    
    Admin->>Firebase: Login with System Tenant Config
    Firebase-->>Admin: ID Token (uid, email)
    
    Admin->>BE: GET /api/platform/auth/me
    BE->>DB: Verify platform_admin role
    BE-->>Admin: 200 {user_info, role: "platform_admin"}

    Note over Admin: 2. Create Tenant Flow
    Admin->>BE: POST /api/platform/tenants {name, domain, admin_email}
    BE->>BE: Verify platform_admin role
    BE->>DB: Check domain uniqueness
    BE->>DB: INSERT tenant (status='pending')
    BE-->>Admin: 200 {id, message}
    
    Note over Admin: 3. Impersonation Flow
    Admin->>BE: POST /api/platform/tenants/{id}/impersonate
    BE->>DB: Verify platform_admin role
    BE->>DB: Find tenant admin user
    BE->>BE: Generate short-lived JWT
    BE-->>Admin: 200 {token, redirect_url}
```

### Steps
1.  **Login**: Authenticates against the dedicated **Platform Tenant**.
2.  **Impersonation**: Generates a short-lived custom JWT that allows the admin to "become" a tenant owner for debugging.
