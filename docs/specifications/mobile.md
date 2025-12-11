# SPEC-07: Mobile App Support

**Status**: Active / Implemented
**Platform**: iOS & Android (React Native)
**Last Updated**: 2025-12-11

## Overview

The Enterprise SSO mobile app allows users to access their tenant workspace on the go. It shares the same backend API as the web platform but utilizes native-specific authentication flows to ensure a secure and seamless user experience.

## 1. Authentication Strategy

Mobile authentication differs from web to support native usability guidelines (avoiding embedded webviews for login).

### 1.1 Native Login (No Webviews)
*   **Technology**: `react-native-app-auth` (AppAuth-iOS / AppAuth-Android).
*   **Flow**:
    1.  User enters email.
    2.  `POST /api/b2b/auth/resolve-tenant`: Returns `mobile_provider_id` (OIDC) and config.
    3.  `GET /api/b2b/auth/oidc-config/{provider_id}`: Returns dynamic `issuer` and `client_id` for that tenant.
    4.  App opens System Browser (SFSafariViewController / Chrome Custom Tabs) for IDP login.
    5.  User authenticates with their corporate credentials (e.g., Okta).
    6.  IDP redirects back to App via Deep Link (e.g., `com.company.sso://callback`).

### 1.2 Token Exchange
Since the AppAuth flow returns an IDP Token (not a Firebase Token), we perform a server-side exchange:
*   **Endpoint**: `POST /api/b2b/auth/mobile-login`
*   **Input**: `oidc_id_token`, `provider_id`.
*   **Process**: Backend verifies with GCIP -> Mints **Firebase Custom Token**.
*   **Output**: Firebase Custom Token.
*   **Final Step**: App calls `auth().signInWithCustomToken(token)`.

## 2. Cross-Platform Consistency

### 2.1 Identity Reconciliation
Mobile and Web logins may result in different `firebase_uid` values due to the difference between GCIP Federation (Web) and Custom Token Minting (Mobile).
*   **Solution**: The backend `UserService` treats **Email** as the canonical identity.
*   **Behavior**:
    *   If a Web User logs in on Mobile, the API looks up by Email.
    *   The User ID (UUID) remains the same.
    *   The `firebase_uid` in the database is *not* overwritten if it differs, preserving the stable Web identity while allowing Mobile access.

## 3. Feature Parity & Limitations

| Feature | Web Support | Mobile Support | Notes |
|---------|-------------|----------------|-------|
| SSO Login | ✅ Yes | ✅ Yes | Via Native AppAuth |
| Tenant Switching | ✅ Yes | ⚠️ Partial | Requires re-login currently |
| Dashboard | ✅ Yes | ✅ Yes | Basic Stats |
| User Mgmt | ✅ Yes | ❌ No | Planned for v2 |
| Settings | ✅ Yes | ⚠️ Partial | Read-only |

## 4. Deep Linking

The mobile app supports Universal Links (iOS) and App Links (Android) for seamless workflow handling.

*   `https://app.enterprisesso.com/invite/{token}` -> Opens App -> `InviteAcceptScreen`
*   `https://app.enterprisesso.com/reset-password` -> Opens App -> `ResetPasswordScreen`
