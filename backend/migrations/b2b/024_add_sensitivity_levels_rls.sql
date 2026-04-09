-- Migration: 024_add_sensitivity_levels_rls.sql
-- Purpose: Enable Row Level Security (RLS) for data classification sensitivity levels

-- 1. Enable RLS
ALTER TABLE b2b.sensitivity_levels ENABLE ROW LEVEL SECURITY;

-- 2. Create Isolation Policy
DROP POLICY IF EXISTS sensitivity_level_isolation_policy ON b2b.sensitivity_levels;
CREATE POLICY sensitivity_level_isolation_policy ON b2b.sensitivity_levels
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- 3. Ensure Index exists
CREATE INDEX IF NOT EXISTS idx_sensitivity_levels_tenant_rls ON b2b.sensitivity_levels(tenant_id);

COMMENT ON POLICY sensitivity_level_isolation_policy ON b2b.sensitivity_levels IS 'Enforces tenant isolation for sensitivity levels (data classification plugin)';
