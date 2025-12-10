# Authentication Architecture

**Audience:** Mobile Developers, Backend Engineers

This document details the authentication flows for both Web and Mobile clients, focusing on how the backend establishes identity and isolation context before processing requests.

---

## 1. Request Lifecycle ("The Traffic Cop") 🛡️

Every incoming request must be validated and routed to the correct tenant context **before** it reaches the business logic.

```mermaid
graph TD
    Request[Incoming Request + Firebase JWT] --> AuthMiddleware[B2B Auth Middleware]
    AuthMiddleware -->|Extract Token| Verify{Verify Signature}
    Verify -->|Invalid| 401[401 Unauthorized]
    
    Verify -->|Valid| ExtractTenant[Extract firebase.tenant]
    
    ExtractTenant --> Resolve{Resolve Internal Tenant}
    Resolve -->|Not Found| 401
    Resolve -->|Found| SetRLS[SET app.current_tenant_id]
    
    SetRLS --> Handler[Route Handler]
    Handler --> DB[Database Query]
    
    subgraph Database
        DB --> Policy{RLS Policy Check}
        Policy -->|Match| Row[Return Row]
        Policy -->|No Match| Empty[Return Empty/404]
    end
```

### Key Components
-   **Firebase JWT**: Contains `firebase.tenant` (external ID).
-   **Tenant Resolution**: Maps external `firebase_tenant_id` → internal UUID.
-   **RLS Context**: `app.current_tenant_id` is set *per request*, ensuring all DB queries are automatically scoped.


## 2. Web Application Authentication 💻

The Web App follows the standard **Firebase Identity Platform (GCIP)** flow using the Firebase JS SDK.


### Web Login Sequence

```mermaid
sequenceDiagram
    participant Browser as Web App (React)
    participant BE as Backend API
    participant Firebase as Firebase Identity
    participant IdP as Auth0 / IDP
    participant DB as Postgres DB

    Note over Browser: 1. Tenant Resolution
    Browser->>BE: POST /api/b2b/auth/resolve_tenant {email}
    BE-->Browser: 200 {firebase_tenant_id, oidc_provider_id}

    Note over Browser: 2. Initiate Login
    Browser->>Firebase: auth.tenantId = firebase_tenant_id
    Browser->>Firebase: signInWithPopup(provider)
    
    Firebase->>IdP: OIDC Redirect
    IdP-->>Firebase: Authenticated
    Firebase-->>Browser: ID Token (JWT) + User Profile
    Note right of Firebase: Identity created in Firebase

    Note over Browser: 3. Sync User (Creation)
    Browser->>BE: POST /api/b2b/auth/sync-user
    BE->>BE: Verify Firebase Token
    BE->>BE: Resolve Tenant (from token)
    BE->>DB: Upsert User (email matches)
    Note right of BE: User created in Postgres here
    BE-->>Browser: 200 OK (Role + Context)
```

### Key Differences from Mobile
-   **Client-Side Driven**: The browser handles the entire OAuth handshake via Firebase SDK.
-   **Firebase-Issued Tokens**: The ID Token is signed directly by Firebase.
-   **Identity Creation**: Occurs immediately when user completes IDP login flow.

---

## 3. Mobile Native Authentication 📱

Mobile apps cannot use the standard Firebase Web SDK's popup/redirect flow. Instead, they use a "Native" flow involving **Auth0** and **Firebase Custom Tokens**.

### Architecture Comparison

| Aspect | Web | Mobile Native |
|--------|-----|---------------|
| **OAuth Flow** | Firebase GCIP handles OIDC | Direct Auth0 OAuth + Custom Token |
| **Firebase Token** | GCIP issues token after popup | Backend issues Custom Token |
| **Tenant API** | Browser popup with tenant set | `auth().setTenantId()` async method |
| **User Identity** | GCIP-generated UID | Backend-generated UID (email-based) |

### Mobile Login Sequence

```mermaid
sequenceDiagram
    participant App as Mobile App (React Native)
    participant BE as Backend API
    participant Auth0 as Auth0 IdP
    participant Firebase as Firebase Auth
    participant DB as Database

    Note over App: 1. Tenant Resolution
    App->>BE: POST /api/b2b/auth/resolve-tenant {email}
    BE->>DB: SELECT tenant by domain
    BE-->>App: {firebase_tenant_id, oidc_provider_id}

    Note over App: 2. Get OIDC Config
    App->>BE: GET /api/b2b/auth/oidc-config/{provider_id}
    BE-->>App: {issuerUrl, clientId}

    Note over App: 3. Direct OAuth (System Browser)
    App->>Auth0: OAuth Authorization Request (PKCE)
    Auth0-->>App: OIDC ID Token (JWT)

    Note over App: 4. Backend Token Exchange
    App->>BE: POST /api/b2b/auth/mobile-login<br/>{oidc_id_token, email, firebase_tenant_id}
    BE->>BE: Verify OIDC Token (JWKS)
    BE->>DB: Lookup/Create User (email-based)
    BE->>Firebase: Create Custom Token (tenant-aware)
    BE-->>App: {firebase_custom_token, user_info}

    Note over App: 5. Firebase Sign-In
    App->>Firebase: setTenantId(firebase_tenant_id)
    App->>Firebase: signInWithCustomToken(token)
    Firebase-->>App: UserCredential
```

### Integration Notes
-   **Endpoint**: `POST /api/b2b/auth/mobile-login`
-   **Client Lib**: `react-native-app-auth`
-   **React Native**: Must use `await auth().setTenantId(id)` **method**, not property assignment.

---

## 4. Email-Based User Identity

To ensure users are recognized as the **same identity** across Web (Firebase UID) and Mobile (Custom UID), we use **Email** as the canonical identifier.

| Platform | UID Generation | Example UID |
|----------|----------------|-------------|
| **Web** | Firebase GCIP | `oidc.auth0-company:auth0\|abc123...` |
| **Mobile** | Custom Token | `oidc-john_acme_com` |

**Resolution Logic**:
1.  Backend looks up user by `(tenant_id, email)`.
2.  Updates `firebase_uid` to match the *current* login method.

### Identity Creation Strategy

Since we support both Web (standard OIDC) and Mobile (Native Auth0), the creation of the **Firebase User Record** happens at different times:

| Scenario | Trigger | Identity Created In Firebase | Backend User Created |
|----------|---------|------------------------------|----------------------|
| **Web Login** | User completes SSO Popup | **Immediately** (Client-side via GCIP) | At `/sync-user` call |
| **Mobile Login** | App exchanges Auth0 token | **Delayed** (Upon first `signInWithCustomToken`) | At `/mobile-login` (implicit) |
| **Web Invite** | User accepts & logs in | **Before Join** (Must login to accept) | At `/join` call |
| **Mobile Invite** | User deep-links & logs in | **After Token Exchange** | At `/join` call |

**Crucial Logic**: The backend treats **Email** as the immutable identifier. When a user logs in via a new method (e.g., switched from Web to Mobile), the backend updates the stored `firebase_uid` to match the current session's UID, ensuring continuity.
