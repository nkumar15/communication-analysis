# Growth Workflows: Onboarding & Invitations

**Audience:** Product Managers, Frontend Developers, Backend Engineers

This document visualizes the core growth workflows: **Tenant Activation** (Onboarding), **User Invitation**, and **Platform Administration**.

For lower-level details on how requests are secured, see:
-   [Authentication Architecture](./authentication.md) - Request lifecycle & Mobile Auth
-   [Multi-Tenant Isolation](./multi-tenant-isolation.md) - RLS Mechanics

---

## 1. Tenant Activation Flow 🚀

How a "Pending" tenant becomes "Active" via the owner's first login.

```mermaid
sequenceDiagram
    participant Browser as UI Browser
    participant BE as Backend API
    participant DB as Database
    participant Front as Front‑end (React)
    participant Firebase as Firebase

    Browser->>BE: POST /api/tenants (create tenant)
    BE->>DB: INSERT tenant record
    BE-->>Browser: 201 Created (tenant_id)

    Browser->>BE: POST /api/invitations (create invitation)
    BE->>DB: INSERT invitation with token
    BE-->>Browser: 201 Created (invitation_token)

    Browser->>BE: GET /api/invitations/{token}
    BE->>DB: SELECT invitation
    BE-->>Browser: 200 OK (activation URL)

    Browser->>Front: Open activation URL (http://localhost:3000/activate/TOKEN)
    Front->>BE: GET /api/activate/validate/TOKEN
    BE->>DB: SELECT tenant & invitation, check expiry
    BE-->>Front: 200 ValidationResponse (tenant info)

    Front->>BE: GET /api/activate/tenant-info/{tenant_id}
    BE->>DB: SELECT tenant (firebase_tenant_id, oidc_provider_id)
    BE-->>Front: 200 JSON (SSO config)

    Front->>Firebase: Open OIDC login popup
    Firebase-->>Front: ID token (uid, email, email_verified)

    Front->>BE: POST /api/activate/complete {activation_token}
    BE->>DB: SELECT tenant FOR UPDATE
    BE->>DB: CHECK activation_started_at / expiry
    BE->>DB: UPDATE tenant.activation_started_at (if first call)
    BE->>DB: SELECT user by firebase_uid
    BE->>DB: INSERT user if not exists (admin role)
    BE->>DB: UPDATE invitation.accepted_at
    BE->>DB: UPDATE tenant.status = 'active'
    BE-->>Front: 200 {message, tenant_id, tenant_name}

    Front->>BE: GET /api/activate/check-status/{token}
    BE->>DB: SELECT invitation & user
    BE-->>Front: {status: "ready"|"pending", user_created: bool}
```

### Key API Steps
1.  **Validate Token**: `GET /api/activate/validate/{token}` - Public endpoint (Bypasses RLS). Checks if tenant is pending.
2.  **Complete Activation**: `POST /api/activate/complete` - Requires Firebase Login. Transitions tenant state Pending → Active.

---

## 2. User Invitation Flow 📩

How an existing tenant admin invites a new member.

```mermaid
sequenceDiagram
    participant Admin as Admin (Browser)
    participant BE as Backend API
    participant DB as Database
    participant Front as Front‑end (React)
    participant Invite as Invitee (Browser)
    participant Firebase as Firebase

    Admin->>BE: POST /api/invitations (create invitation)
    BE->>DB: INSERT invitation
    BE-->>Admin: 201 Created (invitation_token)

    Admin->>Invite: Receive invitation email with link
    Invite->>Front: Open invitation URL (http://localhost:3000/invite/TOKEN)
    Front->>BE: GET /api/invitations/{token}
    BE->>DB: SELECT invitation (RLS Bypass)
    BE-->>Front: 200 Invitation details (email, role)

    Front->>Invite: Show Accept button
    Invite->>Front: Click Accept
    Front->>BE: POST /api/invitations/accept {token}
    BE->>DB: UPDATE invitation.accepted_at
    BE-->>Front: 200 Accepted

    Front->>Invite: Prompt SSO login
    Invite->>Firebase: Open OIDC login popup
    Firebase-->>Invite: ID token (uid, email)

    Front->>BE: POST /api/invitations/join {token}
    BE->>DB: Verify Token + User
    BE->>DB: INSERT user into tenant
    BE-->>Front: 200 Join Success
```

### RLS Bypass Strategy (Critical)
Since the `GET /invitations/{token}` endpoint is public (no user context yet), it uses a special **RLS Bypass** pattern:
1.  Router temporarily grants **Platform Admin** context (`app.is_platform_admin=true`).
2.  Looks up token globally across all tenants.
3.  Once found, immediately **scopes down** to that specific tenant (`set_tenant_context`) for subsequent operations.

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
