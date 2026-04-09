---
trigger: always_on
---

# Database Migration Standards

## Scope
Owned by: **Backend Architect**
Applies to: **Every change that touches a SQLAlchemy model, schema, or DB structure**

---

## 1. When a Migration Is Required

A migration file **MUST** be created whenever any of the following change:

| Change | Example |
|--------|---------|
| New table | New SQLAlchemy model class |
| New column | Adding a field to an existing model |
| Removed or renamed column | Dropping/renaming a model field |
| New index | `Column(..., index=True)` or explicit `CREATE INDEX` |
| New FK relationship | `ForeignKey(...)` on a column |
| New unique constraint | `unique=True` or `UniqueConstraint` |
| RLS policy change | New table or tenant_id column added |
| Schema creation | New `__table_args__ = {"schema": "..."}` |

Do **not** create a migration for:
- JSONB content changes (seed data only)
- Python-only changes (services, schemas, tests)
- Altering `server_default` values that don't change existing data

---

## 2. File Naming Convention

```
backend/migrations/{product}/{NNN}_{short_description}.sql
```

- `{product}`: `b2b`, `b2c`, `platform`, or `core`
- `{NNN}`: next sequential number (zero-padded to 3 digits, check existing files)
- `{short_description}`: snake_case, describes the change (not the ticket)

**Examples:**
```
028_add_region_sensitivity_to_alerts.sql
029_add_clearance_level_to_team_role_definitions.sql
030_add_team_region_id.sql
```

To find the next number:
```bash
ls backend/migrations/{product}/ | sort | tail -1
```

---

## 3. Migration File Structure

Every migration file must follow this template:

```sql
-- Migration {NNN}: {short_description}
-- Purpose: {one sentence explaining why this change is needed}

-- {Step 1 comment}
ALTER TABLE {schema}.{table}
    ADD COLUMN IF NOT EXISTS {column} {type} {constraints};

-- Index (if column will be used in WHERE clauses)
CREATE INDEX IF NOT EXISTS idx_{table}_{column}
    ON {schema}.{table} ({column});

-- Backfill existing rows (if column is NOT NULL or has a meaningful default)
UPDATE {schema}.{table}
SET {column} = {default_expression}
WHERE {column} IS NULL;
```

**Always use:**
- `IF NOT EXISTS` / `IF EXISTS` — migrations must be idempotent (safe to re-run)
- `ADD COLUMN IF NOT EXISTS` — never bare `ADD COLUMN`
- `CREATE INDEX IF NOT EXISTS` — never bare `CREATE INDEX`
- `DROP CONSTRAINT IF EXISTS` before re-adding constraints

---

## 4. Mandatory Schema Requirements

Every new tenant-scoped table **MUST** include:

```sql
CREATE TABLE {schema}.{table} (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    -- ... columns ...
    created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_{table}_tenant_id ON {schema}.{table} (tenant_id);
```

Then enable RLS:

```sql
ALTER TABLE {schema}.{table} ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS {table}_isolation_policy ON {schema}.{table};
CREATE POLICY {table}_isolation_policy ON {schema}.{table}
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
```

Global/shared tables (no tenant isolation) must explicitly **disable** RLS:
```sql
ALTER TABLE {schema}.{table} DISABLE ROW LEVEL SECURITY;
```

---

## 5. Model ↔ Migration Sync Checklist

Before committing any model change, verify:

- [ ] Migration file exists with the next sequential number
- [ ] Every new `Column(...)` in the model has a matching `ADD COLUMN IF NOT EXISTS` in the migration
- [ ] Every new `index=True` has a matching `CREATE INDEX IF NOT EXISTS`
- [ ] New FK columns have `ON DELETE` behaviour explicitly set (`CASCADE`, `SET NULL`, or `RESTRICT`)
- [ ] New tenant-scoped tables have `tenant_id`, `created_at`, `updated_at`, UUID PK, and RLS policy
- [ ] Non-nullable new columns either have a `server_default` or include a backfill `UPDATE`
- [ ] Migration is idempotent (`IF NOT EXISTS` / `IF EXISTS` everywhere)

---

## 6. Never Do This

```sql
-- ❌ Not idempotent — fails on re-run
ALTER TABLE b2b.users ADD COLUMN clearance_level INTEGER;
CREATE INDEX idx_users_clearance ON b2b.users (clearance_level);

-- ❌ Missing RLS on a new tenant-scoped table
CREATE TABLE bank_surveillance.my_new_table (id UUID, tenant_id UUID, ...);
-- (no ENABLE ROW LEVEL SECURITY, no policy)

-- ❌ Non-nullable column with no default or backfill
ALTER TABLE b2b.teams ADD COLUMN IF NOT EXISTS region_code VARCHAR(10) NOT NULL;
-- (existing rows have no value — migration will fail)
```

---

## 7. Running Migrations

```bash
make migrate-schema       # applies all pending migrations via run_migrations.py
make db-recreate          # full drop + recreate (dev only)
```

Migration state is tracked in `public.schema_migrations` (keyed by `{product}/{filename}`).
The runner applies files in alphabetical order within each product directory — sequential
numbering enforces the correct order.
