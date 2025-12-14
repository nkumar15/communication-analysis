# Authentication Architecture

**Audience:** Mobile Developers, Backend Engineers, Architects

This document serves as the **Single Source of Truth** for authentication in the Enterprise SSO system. It details how identity is established, verified, and linked across Web and Mobile platforms, and how Multi-Tenant Isolation (RLS) is enforced.

---

## 1. Core Principles 🛡️

1.  **Identity Federation**: We adhere to the **"One Identity"** rule. Users have a single canonical identity (Email) regardless of login method (Web OIDC vs Mobile Native).
2.  **Stable Anchors**: `firebase_uid` is the stable anchor for DB records. It persists even if metadata changes.
3.  **Tenant Isolation**: Authentication != Authorization. A valid user must also have a valid **Tenant Context** to access data.

### Request Lifecycle ("The Traffic Cop")

Every request follows this specialized middleware pipeline:

```mermaid
graph TD
    Request[Incoming Request + Bearer Token] --> AuthMiddleware[B2B Auth Middleware]
    AuthMiddleware -->|1. Verify Sig| Verify{Valid Firebase Token?}
    Verify -->|No| 401[401 Unauthorized]
    
    Verify -->|Yes| Extract[Extract: uid, email, firebase_tenant_id]
    Extract --> Resolve{Resolving Tenant}
    
    Resolve -->|Lookup by Firebase ID| TenantDB[(Tenants Table)]
    TenantDB -->|Found| SetCtx[SET app.current_tenant_id]
    TenantDB -->|Not Found| 404[404 Tenant Not Found]
    
    SetCtx --> Handler[Route Handler / Business Logic]
    Handler --> Query[SQL Query]
    
    subgraph "Postgres RLS Layer"
        Query --> Policy{Row Level Security}
        Policy -->|Tenant ID Matches| Data[Return Data]
        Policy -->|No Match| Empty[Empty Result]
    end
```

---

## 2. Web Application Authentication 💻

The Web App utilizes the standard **Firebase Identity Platform (GCIP)** SDK flow. This is a "Client-Side Driven" flow where the browser handles the handshake.

### Web Login Sequence

```mermaid
sequenceDiagram
    participant Browser as Web App (React)
    participant BE as Backend API
    participant Firebase as Firebase GCIP
    participant IdP as External IdP (Auth0/Okta)
    participant DB as Postgres DB

    Note over Browser: 1. Tenant Resolution
    Browser->>BE: POST /api/b2b/auth/resolve-tenant {email}
    BE-->Browser: 200 {firebase_tenant_id, oidc_provider_id}
    
    Note over Browser: 2. Federated Login
    Browser->>Firebase: auth.tenantId = firebase_tenant_id
    Browser->>Firebase: signInWithPopup(oidc_provider_id)
    Firebase->>IdP: Redirect / Authorize
    IdP-->>Firebase: SUCCESS (id_token)
    Firebase-->>Browser: Firebase ID Token + UID
    
    Note over Browser: 3. Identity Sync (Critical)
    Browser->>BE: POST /api/b2b/auth/sync-user
    BE->>BE: Verify Token
    BE->>DB: UPSERT User (Match by Email/UID)
    Note right of BE: Ensures User exists in our DB
    BE-->>Browser: 200 {user_id, role, tenant_id}
```

---

## 3. Mobile Native Authentication 📱

Mobile Apps **cannot** use the Web SDK's popup flow. They use a **Native OIDC Flow** combined with a **Server-Side Token Exchange**.

> **Architecture Note:** Mobile often requires a separate OIDC Client ID (Bundle ID vs Web Origin). We support separate `oidc_provider_id` configurations for this valid use case to prevent Audience Mismatch errors.

### Mobile Login Sequence

```mermaid
sequenceDiagram
    participant App as Mobile App
    participant BE as Backend API
    participant Auth0 as Auth0 / IdP
    participant GCIP as Google Identity (GCIP)
    participant DB as Postgres DB

    Note over App: 1. Configuration
    App->>BE: POST /resolve-tenant {email}
    BE-->>App: {firebase_tenant_id, mobile_oidc_provider_id}
    
    App->>BE: GET /oidc-config/{provider_id}
    BE-->>App: {issuer, client_id, scopes}
    
    Note over App: 2. Native OAuth (PKCE)
    App->>Auth0: Authorize (System Browser)
    Auth0-->>App: OIDC ID Token (Subject: "sub")

    Note over App: 3. Token Exchange (The Bridge)
    App->>BE: POST /mobile-login {oidc_token, provider_id, nonce}
    BE->>BE: Validate Nonce
    BE->>GCIP: accounts:signInWithIdp(postBody=oidc_token)
    GCIP->>Auth0: Verify Token Signature
    GCIP-->>BE: Firebase ID Token + UID
    Note right of GCIP: Links to existing user if email matches!
    
    BE-->>App: {firebase_id_token, firebase_uid}

    Note over App: 4. Session Start
    App->>BE: POST /sync-user
    BE->>DB: UPSERT User (Identity Stability)
    BE-->>App: 200 OK
```

### Identity Linking Details
*   **Problem**: Mobile login comes from a different OIDC Client ID than Web.
*   **Solution**: GCIP treats them as two providers, but **Atomically Links them** into a single `firebase_uid` because the **Email Address** matches.
*   **Result**: A user can log in on Web, then Mobile, and share the exact same User ID and Data.

---

## 4. Tenant Activation & Onboarding Flow 🚀

This is the flow where a "Pending" tenant becomes "Active" via the owner's first action.

```mermaid
sequenceDiagram
    participant Owner as Tenant Owner
    participant Web as Web Frontend
    participant BE as Backend API
    participant DB as Database
    
    Note over Owner: Clicking Link in Email
    Owner->>Web: Opens /activate/{token}
    
    Web->>BE: GET /api/activate/validate/{token}
    BE->>DB: Check Token Validity & Expiry
    BE-->>Web: 200 {company_name, email, tenant_id}
    
    Note over Web: 1. Login to Prove Identity
    Web->>BE: GET /activate/tenant-info/{id}
    BE-->>Web: {oidc_provider_id, ...}
    Web->>Firebase: signInWithPopup()
    Firebase-->>Web: ID Token
    
    Note over Web: 2. Finalize Activation
    Web->>BE: POST /activate/complete {token}
    BE->>BE: Verify Token Email == Owner Email
    BE->>DB: UPDATE tenant SET status='active'
    BE->>DB: INSERT User (Role: OWNER)
    BE-->>Web: 200 OK
```

---

## 5. Security & Isolation

### Common Attacks & Defenses

| Attack Vector | Our Defense | Implementation |
|---------------|-------------|----------------|
| **Tenant Hopping** | **Token-Based RLS** | RLS Policy: `Using current_setting('app.current_tenant_id')` ensures query *physically cannot* see other rows. |
| **Identity Spoofing** | **Signature Verification** | `firebase_admin.verify_id_token()` checks cryptographic signature on every request. |
| **Audience Mismatch** | **Nonce Validation** | Mobile flow enforces `nonce` to prevent replay attacks during token exchange. |
| **Dangling Users** | **Soft Deletes** | `deleted_at` column + filtered indices ensure no zombie access. |

### Role Based Access Control (RBAC)
Roles are stored in Postgres (`b2b.roles`) but enforced in Application Logic.
*   **Frontend**: `useAuth()` hook checks permisssions.
*   **Backend**: `User` object injected into route handlers contains `role` slug.

---

**Related Documents:**
*   [Multi-Tenant Isolation](./multi-tenant-isolation.md)
*   [Tenant Onboarding](./tenant-onboarding-flow.md)
