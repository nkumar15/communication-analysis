---
description: Best practices and validation for SQL migrations and database schema design.
---

# Database Inspector

This skill ensures all SQL migrations and schema changes follow established patterns. **Invoke this skill whenever creating or modifying migrations, adding new tables, or changing RLS policies.**

## 1. When to Use

Trigger this skill when the user asks to:
- Create a new table
- Add a column or index
- Write a new migration file
- Modify RLS (Row-Level Security) policies
- Add foreign keys or constraints

## 2. Migration File Standards

### Naming Convention
```
[NNN]_[product]_[description].sql
```
- `NNN`: Three-digit sequence number (e.g., `001`, `015`)
- `product`: Module name (e.g., `b2b`, `b2c`)
- `description`: Snake_case description

**Examples**:
- `001_b2b_core.sql`
- `015_bank_surveillance_plugins.sql`

### File Structure
Each migration file **MUST** include:
```sql
-- ============================================================================
-- [TITLE]
-- ============================================================================
-- [Brief Description of Purpose]
-- ============================================================================

-- ... SQL statements ...
```

### Placement
- **Path**: `backend/migrations/[product]/[NNN]_[name].sql`
- **Products**: `core/`, `platform/`, `b2b/`, `b2c/`

## 3. Schema Design Rules

### Tables
| Rule | Example |
| :--- | :--- |
| **MUST** use `UUID` for primary keys | `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` |
| **MUST** include `created_at`, `updated_at` | `created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL` |
| **SHOULD** include soft delete | `deleted_at TIMESTAMPTZ DEFAULT NULL` |
| **MUST** prefix schema name | `CREATE TABLE b2b.my_table` |

### Tenant Isolation
| Rule | Example |
| :--- | :--- |
| **MUST** have `tenant_id` column on tenant-scoped tables | `tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE` |
| **MUST** create index on `tenant_id` | `CREATE INDEX idx_[table]_tenant_id ON b2b.[table](tenant_id)` |

### Indexes
| Rule | Example |
| :--- | :--- |
| **MUST** index all FKs | `CREATE INDEX idx_users_tenant_id ON b2b.users(tenant_id)` |
| **SHOULD** use partial indexes for soft delete | `WHERE deleted_at IS NULL` |
| **SHOULD** use GIN for JSONB/Array columns | `USING GIN(geographic_scopes)` |

### Constraints
| Rule | Example |
| :--- | :--- |
| **MUST** use explicit constraint names | `CONSTRAINT unique_tenant_email UNIQUE(tenant_id, email)` |
| **MUST** use `ON DELETE CASCADE` for tenant FKs | Standard pattern |
| **SHOULD** use CHECK for enums | `CHECK (status IN ('active', 'pending', 'suspended'))` |

## 4. RLS (Row-Level Security) Pattern

**All tenant-scoped tables MUST have RLS enabled.**

### Standard RLS Policy Template
```sql
-- 1. Enable RLS
ALTER TABLE b2b.[table_name] ENABLE ROW LEVEL SECURITY;

-- 2. Create Policy (Drop first for idempotency)
DROP POLICY IF EXISTS [table]_isolation_policy ON b2b.[table_name];
CREATE POLICY [table]_isolation_policy ON b2b.[table_name]
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
```

### Indirect RLS (Join Table)
For tables without direct `tenant_id` (e.g., `team_members`):
```sql
CREATE POLICY team_member_isolation_policy ON b2b.team_members
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        team_id IN (
            SELECT id FROM b2b.teams 
            WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    );
```

## 5. Checklist Before Committing

- [ ] **Naming**: File follows `[NNN]_[product]_[desc].sql` pattern
- [ ] **Schema**: Table is in correct schema (`b2b.`, `b2c.`, `platform.`)
- [ ] **UUID PKs**: Using `gen_random_uuid()`
- [ ] **Timestamps**: Has `created_at`, `updated_at`
- [ ] **Tenant FK**: Has `tenant_id` with `ON DELETE CASCADE`
- [ ] **Indexes**: All FKs and lookup columns indexed
- [ ] **RLS**: Policy created for tenant isolation
- [ ] **Idempotent**: Uses `IF NOT EXISTS`, `DROP POLICY IF EXISTS`
- [ ] **Soft Delete**: `deleted_at` column if records should not be hard-deleted

## 6. Common Patterns

### Add Column (Idempotent)
```sql
ALTER TABLE b2b.users 
ADD COLUMN IF NOT EXISTS new_column VARCHAR(100);
```

### Update Trigger
```sql
CREATE OR REPLACE FUNCTION b2b.update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER [table]_updated_at 
    BEFORE UPDATE ON b2b.[table] 
    FOR EACH ROW EXECUTE FUNCTION b2b.update_timestamp_column();
```

### Unique Partial Index (Soft Delete Aware)
```sql
CREATE UNIQUE INDEX idx_teams_one_default_per_tenant 
    ON b2b.teams(tenant_id) 
    WHERE is_default = true AND deleted_at IS NULL;
```

## 7. Audit Workflow

When the user asks to "audit migrations", "check schema compliance", or "fix migration divergences", follow this workflow:

### Step 1: Scan Migrations
```bash
# List all migration files
find backend/migrations -name "*.sql" -type f | sort
```

### Step 2: Run Compliance Checks
For each migration file, verify:

| Check | Pattern to Search | Violation |
| :--- | :--- | :--- |
| **File Naming** | `[0-9]{3}_*.sql` | Files not matching `NNN_desc.sql` |
| **Schema Prefix** | `CREATE TABLE [schema].` | Missing schema prefix |
| **UUID Primary Key** | `UUID PRIMARY KEY DEFAULT gen_random_uuid()` | Non-UUID or missing default |
| **Timestamps** | `created_at TIMESTAMPTZ` | Missing or wrong type |
| **Tenant FK** | `tenant_id UUID.*REFERENCES.*tenants` | Missing on tenant-scoped table |
| **RLS Enabled** | `ENABLE ROW LEVEL SECURITY` | Tenant table without RLS |
| **Idempotent DDL** | `IF NOT EXISTS`, `IF EXISTS` | Non-idempotent statements |

### Step 3: Generate Report
Output a compliance report:
```markdown
## Migration Audit Report

### ✅ Passing
- `001_b2b_core.sql`: All checks passed

### ⚠️ Warnings
- `010_add_provider_coupon_id.sql`: Missing header comment block

### ❌ Violations
- `015_enron_tables.sql`: Missing RLS policy for `b2b.enron_emails` table
```

### Step 4: Generate Fix Migration
If violations are found, generate a **new fixup migration**:
```sql
-- ============================================================================
-- FIXUP: [Description of fixes]
-- ============================================================================
-- Auto-generated to address compliance gaps
-- ============================================================================

-- Fix 1: Add missing RLS
ALTER TABLE b2b.enron_emails ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS enron_emails_isolation_policy ON b2b.enron_emails;
CREATE POLICY enron_emails_isolation_policy ON b2b.enron_emails
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- Fix 2: Add missing index
CREATE INDEX IF NOT EXISTS idx_enron_emails_tenant_id ON b2b.enron_emails(tenant_id);
```

### Trigger Phrases
Invoke this audit when user says:
- "Audit the migrations"
- "Check schema compliance"
- "Are there any RLS gaps?"
- "Fix migration issues"

