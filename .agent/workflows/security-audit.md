---
description: Steps to audit any monorepo module for security lapses (RBAC, RLS, Secrets, PII).
---

# Security Audit Workflow

This workflow provides a structured process for auditing monorepo modules (backend, frontend, sql) to ensure compliance with the project's security and architectural standards.

## 1. Backend Router Audit (RBAC)
Routers are the first line of defense. Every endpoint MUST enforce permissions.
- **Goal**: Verify mandatory authentication and authorization.
- **Checks**:
    - Identify all `@router` endpoints.
    - Confirm use of `Depends(get_current_user)` or `Depends(get_current_active_user)`.
    - Verify `rbac_service.check_permission(db, user_id, tenant_id, "resource:action")` is called BEFORE business logic.
    - Check that resource strings match the registered actions in `resources.yaml`.

```bash
# General search for router security patterns
grep -rnE "@router|rbac_service|Depends\(get_current" backend/modules/
```

## 2. Backend Service Audit (RLS & Isolation)
Services own data integrity and MUST ensure tenant isolation.
- **Goal**: Prevent cross-tenant data leakage (IDOR).
- **Checks**:
    - Verify methods accept `tenant_id: UUID` (for B2B/B2C).
    - ensure EVERY SQLAlchemy `select()` or `update()` includes `.where(Model.tenant_id == tenant_id)`.
    - Confirm `rls_service.set_tenant_context(db, tenant_id)` is used if raw SQL or intricate joins are involved.

```bash
# Scan for missing tenant_id filters in queries
grep -rn "select(" backend/modules/ | grep -v "tenant_id"
```

## 3. SQL Migration Audit (Defense in Depth)
- **Goal**: Verify Row-Level Security (RLS) is active at the DB layer.
- **Checks**:
    - Every table has `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`.
    - Tenant-scoped tables have a corresponding `CREATE POLICY ... USING (tenant_id = ...)`.
    - All `tenant_id` columns are indexed for performance and isolation stability.

```bash
# Check for tables lacking RLS enablement
grep -rL "ENABLE ROW LEVEL SECURITY" backend/migrations/
```

## 4. Credential & Secret Audit
- **Goal**: Prevent hardcoding of sensitive keys.
- **Checks**:
    - Scan for prefixes like `sk_`, `pk_`, `AI_KEY`, `SECRET`.
    - Ensure all secrets are fetched via `Settings` or environment variables.
    - Verify `.env.example` contains the keys used in code.

```bash
# Scan for suspicious hardcoded strings
grep -rnE "sk_|key_|token_|secret_|password_" . --exclude-dir={.venv,node_modules,dist}
```

## 5. Reporting
Findings should be summarized in a report documenting:
- **Scope**: The directory or module audited.
- **Violations**: Logical file path and line number of the security lapse.
- **Remediation**: Required code changes to meet the standard.
