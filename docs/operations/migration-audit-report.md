# Migration Audit Report

**Date**: 2026-01-19
**Scope**: `backend/migrations/` (32 files across 4 products)

---

## ✅ Passing

| File | Status |
| :--- | :--- |
| `001_b2b_core.sql` | All checks passed |
| `002_b2b_rbac.sql` | All checks passed |
| `003_b2b_security_rls.sql` | All checks passed |
| `004_b2b_billing.sql` | All checks passed |
| `005_b2b_growth.sql` | All checks passed |
| `006_b2b_audit_logs.sql` | All checks passed |
| `007_b2b_module_domain.sql` | All checks passed |
| `008_b2b_billing_foundation.sql` | All checks passed |
| `015_bank_surveillance_plugins.sql` | All checks passed |
| `016_bank_surveillance_tables.sql` | All checks passed |
| `001_b2c_core.sql` | All checks passed |
| `002_b2c_invitations.sql` | All checks passed |
| `003_b2c_subscriptions.sql` | All checks passed |
| `004_b2c_module_todos.sql` | All checks passed |
| `005_b2c_admin_permissions.sql` | All checks passed |
| `007_workspace_member_user_visibility.sql` | All checks passed |
| `009_b2c_user_billing_profile.sql` | All checks passed |
| `001_platform_core.sql` | All checks passed |
| `002_platform_permissions.sql` | All checks passed |

---

## ⚠️ Warnings (Missing Header Comment Block)

These files lack the standard header comment block:

| File | Issue |
| :--- | :--- |
| `b2b/010_add_provider_coupon_id.sql` | Missing `-- ==` header |
| `b2b/012_add_action_applicable_resources.sql` | Missing header |
| `b2b/013_rag_tables.sql` | Missing header |
| `b2b/015_enron_tables.sql` | Missing header |
| `b2b/016_add_tenant_id_to_enron.sql` | Missing header |
| `b2b/017_add_tenant_plugins.sql` | Missing header |
| `b2b/018_add_scope_levels.sql` | Missing header |
| `b2c/006_add_member_status.sql` | Missing header |
| `b2c/008_add_invoice_periods.sql` | Missing header |
| `b2c/010_add_provider_coupon_id.sql` | Missing header |
| `b2c/011_b2c_finance_trader_rag.sql` | Missing header |
| `b2c/012_add_es_indexed_count.sql` | Missing header |
| `core/001_init.sql` | Missing header |

---

## ❌ Violations

### 1. Misplaced Migration
| File | Issue |
| :--- | :--- |
| `b2b/013_rag_tables.sql` | Creates `b2c_finance_trader` schema but is in `b2b/` folder. Should be in `b2c/`. |

### 2. Missing Tenant Isolation (`tenant_id` + RLS)
| File | Table | Issue |
| :--- | :--- | :--- |
| `b2b/015_enron_tables.sql` | `bank_surveillance.enron_emails` | Missing `tenant_id` column |
| `b2b/015_enron_tables.sql` | `bank_surveillance.enron_emails` | Missing RLS policy |

### 3. Duplicate Sequence Numbers
| Sequence | Files |
| :--- | :--- |
| `015` | `015_bank_surveillance_plugins.sql`, `015_enron_tables.sql` |
| `016` | `016_add_tenant_id_to_enron.sql`, `016_bank_surveillance_tables.sql` |

---

## Recommended Fixes

### Fix 1: Move misplaced migration
Move `b2b/013_rag_tables.sql` to `b2c/` folder with appropriate renaming.

### Fix 2: Create fixup migration for enron_emails
```sql
-- ============================================================================
-- FIXUP: Add tenant isolation to enron_emails
-- ============================================================================

-- Add tenant_id column
ALTER TABLE bank_surveillance.enron_emails 
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES b2b.tenants(id) ON DELETE CASCADE;

-- Add index
CREATE INDEX IF NOT EXISTS idx_enron_emails_tenant_id 
ON bank_surveillance.enron_emails(tenant_id);

-- Enable RLS
ALTER TABLE bank_surveillance.enron_emails ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS enron_emails_isolation_policy ON bank_surveillance.enron_emails;
CREATE POLICY enron_emails_isolation_policy ON bank_surveillance.enron_emails
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
```

### Fix 3: Renumber duplicate migrations
Renumber to avoid sequence collisions.
