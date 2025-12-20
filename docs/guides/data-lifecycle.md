# Data Lifecycle & Deletion Guide

This document outlines how tenant data is managed, deleted, and retained within the platform.

## 1. Soft Delete (Default)

The application implements a **Soft Delete** strategy by default for all tenant operations. This ensures accidental deletions can be recovered and maintains data for audit purposes.

### How it works
When a Platform Admin "deletes" (or deactivates) a tenant via the API/Dashboard:
1.  **NO data is removed** from the database.
2.  The tenant record is updated:
    - `deleted_at` timestamp is set.
    - `is_active` is set to `FALSE`.
3.  **Child Records** (Users, Teams, etc.):
    - Are **NOT** modified.
    - Remain in the database.
    - Are inaccessible because the parent Tenant is inactive/deleted (enforced by RLS and Middleware).

### Recovery
Soft-deleted tenants can be restored by a database administrator by setting `deleted_at = NULL` and `is_active = TRUE`.

---

## 2. Hard Delete (Permanent Removal)

If a tenant requests full data removal (e.g., for GDPR/CCPA compliance), you must perform a **Hard Delete** directly in the database.

### How it works
The database schema utilizes PostgreSQL `ON DELETE CASCADE` constraints on all child tables. This means deleting the Text record will automatically and instantly remove all associated data.

### Cascading Scope
Deleting a row from `b2b.tenants` will automatically delete:
- All **Users** (`b2b.users`)
- All **Teams** (`b2b.teams`)
- All **Roles** (`b2b.roles`)
- All **Audit Logs** (`b2b.audit_log`) *
- All **Auth Providers** (`b2b.auth_providers`)

*\* Note: Audit logs are typically cascaded, but check your specific compliance requirements. You may want to archive them before deletion.*

### Execution
To permanently wipe a tenant and all its data:

```sql
-- 1. Identify the tenant UUID
SELECT id, name, domain FROM b2b.tenants WHERE domain = 'target-domain.com';

-- 2. Execute Hard Delete
DELETE FROM b2b.tenants WHERE id = 'uuid-from-step-1';
```

**⚠️ WARNING: This operation is IRREVERSIBLE.**

---

## 3. Data Retention Policy

- **Active Tenants**: Data retained indefinitely.
- **Soft Deleted**: Retained until manually purged or hard deleted.
- **Audit Logs**: Retained indefinitely by default.

### Automated Cleanup (Optional)
To automatically purge soft-deleted tenants after 30 days, you can run a scheduled cron job:

```sql
DELETE FROM b2b.tenants 
WHERE deleted_at < NOW() - INTERVAL '30 days';
```
Due to cascade constraints, this will efficiently wipe all ready-to-purge data.
