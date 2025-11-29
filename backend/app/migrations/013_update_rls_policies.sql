-- Migration 013: Update RLS Policies for Schema-Qualified Tables
-- Updates existing Row-Level Security policies to work with new schema names

-- Drop old RLS policies (they reference tables without schema)
-- We'll recreate them with schema-qualified table names

-- B2B Users table RLS
DROP POLICY IF EXISTS tenant_isolation_policy ON users;
DROP POLICY IF EXISTS tenant_isolation_policy ON b2b.users;

-- Enable RLS on b2b.users
ALTER TABLE b2b.users ENABLE ROW LEVEL SECURITY;

-- Create new policy with schema-qualified table name
CREATE POLICY tenant_isolation_policy ON b2b.users
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

-- B2B Roles table RLS
DROP POLICY IF EXISTS tenant_isolation_policy ON roles;
DROP POLICY IF EXISTS tenant_isolation_policy ON b2b.roles;

ALTER TABLE b2b.roles ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON b2b.roles
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

-- B2B Invitations table RLS
DROP POLICY IF EXISTS tenant_isolation_policy ON invitations;
DROP POLICY IF EXISTS tenant_isolation_policy ON b2b.invitations;

ALTER TABLE b2b.invitations ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON b2b.invitations
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

-- Farming Farmers table RLS
DROP POLICY IF EXISTS tenant_isolation_policy ON farmers;
DROP POLICY IF EXISTS tenant_isolation_policy ON farming.farmers;

ALTER TABLE farming.farmers ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON farming.farmers
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

-- B2B Resources and Actions (no tenant_id, so no RLS needed)
-- These are global reference tables

-- Verify RLS policies
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    -- Check b2b.users has RLS policy
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'b2b' AND tablename = 'users' AND policyname = 'tenant_isolation_policy';
    
    IF policy_count = 0 THEN
        RAISE EXCEPTION 'RLS policy not found for b2b.users';
    END IF;
    
    -- Check b2b.roles has RLS policy
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'b2b' AND tablename = 'roles' AND policyname = 'tenant_isolation_policy';
    
    IF policy_count = 0 THEN
        RAISE EXCEPTION 'RLS policy not found for b2b.roles';
    END IF;
    
    -- Check b2b.invitations has RLS policy
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'b2b' AND tablename = 'invitations' AND policyname = 'tenant_isolation_policy';
    
    IF policy_count = 0 THEN
        RAISE EXCEPTION 'RLS policy not found for b2b.invitations';
    END IF;
    
    -- Check farming.farmers has RLS policy
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'farming' AND tablename = 'farmers' AND policyname = 'tenant_isolation_policy';
    
    IF policy_count = 0 THEN
        RAISE EXCEPTION 'RLS policy not found for farming.farmers';
    END IF;
    
    RAISE NOTICE 'All RLS policies updated successfully';
END $$;
