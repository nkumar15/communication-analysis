-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================
-- Implements PostgreSQL Row Level Security for tenant isolation
--
-- Security Model:
--   - All queries must set app.current_tenant_id session variable
--   - Queries without tenant context return empty results
--   - Database-level enforcement prevents cross-tenant data leaks
--   - Migrations run as superuser (bypass RLS)
-- ============================================================================

-- ============================================================================
-- USERS TABLE RLS
-- ============================================================================

ALTER TABLE b2b.users ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see users in their tenant
CREATE POLICY tenant_isolation_users ON b2b.users
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

COMMENT ON POLICY tenant_isolation_users ON b2b.users IS 
    'Enforces tenant isolation - users can only access data from their own tenant';

-- ============================================================================
-- INVITATIONS TABLE RLS
-- ============================================================================

ALTER TABLE b2b.invitations ENABLE ROW LEVEL SECURITY;

-- Policy: Invitations scoped to tenant
CREATE POLICY tenant_isolation_invitations ON b2b.invitations
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

COMMENT ON POLICY tenant_isolation_invitations ON b2b.invitations IS 
    'Enforces tenant isolation for invitations';

-- ============================================================================
-- ROLES TABLE RLS
-- ============================================================================

ALTER TABLE b2b.roles ENABLE ROW LEVEL SECURITY;

-- Policy: Roles scoped to tenant
CREATE POLICY tenant_isolation_roles ON b2b.roles
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

COMMENT ON POLICY tenant_isolation_roles ON b2b.roles IS 
    'Enforces tenant isolation for roles';

-- ============================================================================
-- VERIFICATION: Ensure all B2B RLS policies are created
-- ============================================================================
-- Note: Domain-specific tables (farmers) have RLS in their own migrations

DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    -- Check b2b.users has RLS policy
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'b2b' AND tablename = 'users' AND policyname = 'tenant_isolation_users';
    
    IF policy_count = 0 THEN
        RAISE EXCEPTION 'RLS policy not found for b2b.users';
    END IF;
    
    -- Check b2b.roles has RLS policy
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'b2b' AND tablename = 'roles' AND policyname = 'tenant_isolation_roles';
    
    IF policy_count = 0 THEN
        RAISE EXCEPTION 'RLS policy not found for b2b.roles';
    END IF;
    
    -- Check b2b.invitations has RLS policy
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'b2b' AND tablename = 'invitations' AND policyname = 'tenant_isolation_invitations';
    
    IF policy_count = 0 THEN
        RAISE EXCEPTION 'RLS policy not found for b2b.invitations';
    END IF;
    
    RAISE NOTICE 'All B2B RLS policies created successfully';
END $$;

-- ============================================================================
-- NOTES
-- ============================================================================

-- The tenants table does NOT have RLS enabled because:
--   1. It's the lookup table for tenant resolution
--   2. Users need to query it by domain/email before authentication
--   3. Application logic handles access control for tenant data

-- To use RLS in application code:
--   SET LOCAL app.current_tenant_id = '<tenant_uuid>';
--   -- Run queries
--   RESET app.current_tenant_id;

-- RLS policies use USING clause (for SELECT):
--   - Controls which rows are visible to queries
--   - Returns empty result set if tenant context not set
--   - Superuser and table owner bypass RLS
