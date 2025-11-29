# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

Please report vulnerabilities to `security@enterprisesso.com`. We will respond within 48 hours.

## Security Architecture & Features

This project implements a "Secure by Design" multi-tenant architecture.

### 1. Authentication & Identity
- **Firebase Auth Integration**: All authentication is handled via Firebase Identity Platform (OIDC/SAML).
- **Token Verification**: Backend strictly validates Firebase ID tokens including `email_verified` claims.
- **Mocking for Tests**: A custom, dependency-free mocking system allows full E2E testing of auth flows without external dependencies.

### 2. Multi-Tenant Isolation
- **Database Level**: Tenant ID is enforced on all queries via service layer logic.
- **API Level**: Strict checks ensure users can only access data belonging to their verified tenant context.
- **Cross-Tenant Prevention**: Explicit tests (`tests/security/test_multi_tenant_isolation.py`) verify that data leakage between tenants is blocked.

### 3. Invitation & Onboarding Security
- **Email Verification Enforcement**: Users MUST have a verified email in Firebase to accept invitations.
- **PII Minimization**: Public invitation validation endpoints return only the absolute minimum data (Tenant Name, Email) and strip internal IDs.
- **Timing Attack Resistance**: Token lookups use constant-time comparison (`secrets.compare_digest`).
- **Audit Logging**: All invitation acceptances record:
    - `accepted_by` (User ID)
    - `accepted_from_ip` (Client IP)
    - `user_agent` (Browser info)

### 4. Activation Security
- **Single-Use Tokens**: Activation tokens are invalidated immediately upon use.
- **Replay Attack Prevention**: Atomic database locks and timestamp checks prevent concurrent activation attempts.
- **Grace Period**: A 5-minute grace period handles network retries while blocking malicious replays.

## Testing Security
We maintain a dedicated security test suite. Run it with:
```bash
make test-security
```
This suite verifies:
- Tenant isolation
- PII leakage
- Auth enforcement
- Token validation logic
