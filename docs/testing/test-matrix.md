# Test Matrix

This document maps functional requirements to specific test files, ensuring comprehensive coverage across API and Browser layers.

**Status Legend:**
- ✅ : Fully Covered
- ⚠️ : Partially Covered / WIP
- ❌ : Not Covered / Manual Only

## 1. Tenant Onboarding (Invite-Based)

**Ref:** [`docs/specifications/tenant-onboarding.md`](../specifications/tenant-onboarding.md) (SPEC-01)

| ID | Requirement | API Test | Browser Test | Status |
|----|-------------|----------|--------------|--------|
| **ONB-01** | **Platform Admin Invite**: Platform admin can invite a new tenant owner via API/CLI | `tests/e2e_api/platform/test_tenants.py` | `tests/e2e_browser/test_platform_admin.py` | ⚠️ (Browser WIP) |
| **ONB-02** | **Activation Email**: System generates valid activation token and "sends" email | `tests/e2e_api/b2b/test_activation.py` | *Implicit in ONB-03* | ✅ |
| **ONB-03** | **Owner Activation**: Tenant owner can click link, SSO login, and activate account | `tests/e2e_api/b2b/test_activation.py` | `tests/e2e_browser/test_tenant_onboarding.py` | ⚠️ (Browser Skipped) |
| **ONB-04** | **Token Expiry**: Activation link fails if expired (>48h) | `tests/e2e_api/b2b/test_activation.py` | *Manual* | ✅ (API Only) |

## 2. Authentication & Isolation

**Ref:** `docs/architecture/multi-tenant-isolation.md`

| ID | Requirement | API Test | Browser Test | Status |
|----|-------------|----------|--------------|--------|
| **AUTH-01** | **SSO Login**: Existing user can login via OIDC (Firebase mock/custom token) | `tests/e2e_api/b2b/test_auth.py` | `tests/e2e_browser/test_login_flow.py` | ✅ |
| **SEC-01** | **Cross-Tenant Block**: Tenant A cannot access Tenant B's data | `tests/e2e_api/b2b/test_security.py` | *N/A (API enforcement)* | ✅ |
| **SEC-02** | **Unactivated Block**: Users in "Pending" tenants cannot login | `tests/e2e_api/b2b/test_auth.py` | *N/A* | ✅ |

## 3. User Management (Tenant Level)

**Ref:** `docs/guides/tenant-admin.md`

| ID | Requirement | API Test | Browser Test | Status |
|----|-------------|----------|--------------|--------|
| **USR-01** | **Invite Member**: Tenant Admin can invite `manager` or `member` | `tests/e2e_api/b2b/test_invitations.py` | `tests/e2e_browser/test_invitation_flow.py` | ⚠️ (Browser WIP) |
| **USR-02** | **Accept Invite**: User can accept invite and join tenant | `tests/e2e_api/b2b/test_invitations.py` | `tests/e2e_browser/test_invitation_flow.py` | ⚠️ |
| **USR-03** | **RBAC Enforcement**: `member` cannot invite others | `tests/e2e_api/b2b/test_rbac_permissions.py` | *Manual* | ✅ (API Only) |

## 4. Domain Features (Projects/Teams)

**Ref:** `docs/architecture/domain-apis.md`

| ID | Requirement | API Test | Browser Test | Status |
|----|-------------|----------|--------------|--------|
| **DOM-01** | **Create Project**: User can create project in their tenant | `tests/e2e_api/domain/test_projects.py` | *Pending* | ✅ (API Only) |
| **DOM-02** | **Team Scope**: Project only visible to assigned team members | `tests/e2e_api/domain/test_projects.py` | *Pending* | ✅ (API Only) |

## 5. Platform Administration

**Ref:** `docs/guides/platform-admin.md`

| ID | Requirement | API Test | Browser Test | Status |
|----|-------------|----------|--------------|--------|
| **PLT-01** | **List Tenants**: Super Admin can view all tenants with stats | `tests/e2e_api/platform/test_tenants.py` | *Pending* | ✅ (API Only) |
| **PLT-02** | **Create Tenant**: Super Admin can provision new tenant | `tests/e2e_api/platform/test_tenants.py` | *Pending* | ✅ (API Only) |
| **PLT-03** | **Impersonate**: Super Admin can login as any tenant owner | `tests/e2e_api/platform/test_impersonation.py` | *Pending* | ✅ (API Only) |

