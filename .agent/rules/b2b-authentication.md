# B2B Authentication Rules

## 1. Core Principles
- **One Identity**: Users have a single canonical identity (Email) verified via Firebase. `firebase_uid` is the stable anchor.
- **Tenant Isolation**: Authentication != Authorization. A valid user token MUST be resolved to a specific `tenant_id` context.
- **Statelessness**: Authentication state is maintained via JWT (Firebase ID Token). No server-side sessions for auth.

## 2. Request Lifecycle (Middleware Validation)
Every authenticated request **MUST** pass the following "Traffic Cop" checks in order:
1.  **Token Signature**: Verify Firebase ID Token signature.
2.  **Tenant Resolution**: Resolve `firebase_tenant_id` to internal `tenant_id`.
3.  **Tenant Status**:
    - **Activation Check**: `activation_status == 'active'` (Blocks pending tenants).
    - **Deactivation Check**: `is_active == true` (Blocks suspended tenants).
4.  **User Lookup**: Resolve `firebase_uid` -> `user_id`.
5.  **User Status**: Check `is_active == true` (Blocks deactivated users).
6.  **RLS Context**: Set `app.current_tenant_id` via `rls_service.set_tenant_context()`.

## 3. Platform Specific Flows
- **Web App**: Uses **Client-Side Driven** flow (`signInWithPopup`).
- **Mobile App**: Uses **Native OIDC + Token Exchange** flow.
  - Mobile must NOT use web popups.
  - Backend must support `mobile-login` endpoint for token exchange.

## 4. Tenant Status Management
- **Pending**: Created but owner hasn't clicked activation link. Access **DENIED** (403).
- **Active**: Fully functional. Access **ALLOWED**.
- **Deactivated**: Administratively suspended (e.g., non-payment). Access **DENIED** (403).

## 5. Security Enforcements
- **Nonce Validation**: Mandatory for mobile token exchange to prevent replay attacks.
- **RLS Context**: Must be set per-request and cleared after request.
- **Soft Deletes**: `deleted_at` must be checked during user lookup to prevent "Zombie Access".
