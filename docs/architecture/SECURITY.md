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

### 2. Multi-Tenant Isolation (RLS-Based)

**Database-Level Enforcement:** Row Level Security (RLS) provides defense-in-depth isolation

- **PostgreSQL RLS Policies**: Every query on tenant-scoped tables automatically includes `WHERE tenant_id = current_setting('app.current_tenant_id')`
- **RLS-Protected Tables**: `users`, `roles`, `role_permissions`, `invitations`, `teams`, `team_members`
- **Context Management**: Middleware sets `app.current_tenant_id` before each request
- **Fail-Safe Design**: If context not set, queries return empty results (no data leakage)
- **Cross-Tenant Prevention**: Explicit security tests verify isolation (see [`tests/e2e_api/b2b/test_multi_tenant_isolation.py`](file:///home/neeraj/codes/enterprisesso/backend/tests/e2e_api/b2b/test_multi_tenant_isolation.py))

**Security Guarantees:**
- ✅ Even buggy code cannot access other tenants' data
- ✅ Cross-tenant attempts return 404 (not 403) - doesn't leak existence
- ✅ Multiple layers of defense (JWT → Middleware → RLS)

**Implementation Details:** See [Multi-Tenant Isolation Architecture](./multi-tenant-isolation.md) for complete documentation on:
- Which tables have RLS enabled
- Where RLS context is set in the codebase
- How to extend the application with new RLS-protected features
- Common pitfalls and solutions

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
