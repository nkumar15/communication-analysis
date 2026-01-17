---
trigger: always_on
---

# Multi-Tenancy Rules

## Scope
This  Multi-Tenancy model applies specifically to the **B2B (Business-to-Business)** module. It does not apply to Platform or B2C contexts.

## 1. Core Principle: Strict Tenant Isolation
- **Rule**: Every database operation (Read/Write) **MUST** be scoped to a specific `tenant_id`.
- **Implementation**:
  - **Primary Defense (RLS)**: The system relies on PostgreSQL Row Level Security (RLS) to enforce isolation at the database level.
  - **Defense in Depth**: Application-layer filtering (e.g., adding `.where(Model.tenant_id == tenant_id)`) is **highly recommended** as a secondary safeguard and to ensure efficient index usage.
  - **Validation**: Never trust `tenant_id` from the client payload exclusively. Verify it against the authenticated user's session/token.

## 2. Row Level Security (RLS) Context
- **Rule**: Set the appropriate RLS context before executing business logic.
- **Enforcement**:
  - **Standard B2B Requests**: The `get_current_active_user` middleware in `modules/b2b/middleware/b2b_auth.py` is the **single source** of RLS context enforcement. It calls `rls_service.set_tenant_context(db, tenant.id)` after validating the user's token. All routers using this dependency automatically have RLS context set.
  - **Platform Admin**: Use `await rls_service.set_platform_admin_context(db)` sparingly, only for cross-tenant maintenance operations.
  - **Background Workers**: If a worker processes jobs for multiple tenants, explicitly call `await rls_service.set_tenant_context(db, tenant_id)` for each job.
  - **Special Cases**: For endpoints that bypass `get_current_active_user` (e.g., public invitation acceptance), services must explicitly set RLS context before tenant-scoped queries.

## 3. Data Leakage Prevention
- **Rule**: Ensure strict domain boundaries for user invitations unless explicitly configured otherwise.
- **Checks**:
  - **Invitations**: Verify `email_domain == tenant.domain` before creating an invitation.
  - **Guests**: External domain users must be treated as exceptional 'Guests' with limited privileges if the system enables them.

## 4. Subscription Limits
- **Rule**: Enforce resource limits (e.g., `max_teams`, `max_users`) based on the tenant's active subscription plan.
- **Check**: Perform limit checks *before* resource creation (e.g., inside `create_team` service method). Do not rely on frontend checks.
