# Authentication

> **Status**: ![Status](https://img.shields.io/badge/Status-Complete-green)

Secure, multi-tenant identity management powered by Firebase and OIDC.

## Quick Reference
- [Technical Spec](../technical/authentication.md)
- [API Reference](../technical/api.md#authentication)

## Overview
The Authentication module handles user login, session management, and identity synchronization. It supports:
- **Multi-Tenant Login**: Users are scoped to specific tenants.
- **SSO**: Enterprise Single Sign-On via OIDC/SAML (Google, Microsoft, etc.).
- **Firebase Integration**: Leverages Firebase for secure token handling.

## Workflows

### 1. User Login
**Trigger**: User enters email on login page.
**Process**:
1.  Frontend requests IDP config for tenant.
2.  User redirects to IDP (e.g., Google).
3.  IDP returns token -> exchanged for Firebase Token.
4.  Backend syncs user record and returns session.
**Output**: Authenticated Session + User Context.

### 2. Tenant Switching
**Trigger**: User selects a different tenant.
**Process**: Frontend re-authenticates with new tenant context.
**Output**: New Session scoped to target tenant.

## Implementation Checklist
- [x] Firebase Project Setup
- [x] OIDC provider configuration per tenant
- [x] `user.sync` endpoint implementation
- [x] Session cookie management

## Design Decisions
| Decision | Rationale |
| :--- | :--- |
| **Firebase Auth** | Offloads complex crypto/token management; reliable. |
| **Thin Router** | Auth logic resides in `AuthService`, not the router. |
| **RLS Enforcement** | Database isolation prevents cross-tenant data leaks. |
