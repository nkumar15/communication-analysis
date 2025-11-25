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

ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see users in their tenant
CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

COMMENT ON POLICY tenant_isolation_users ON users IS 
    'Enforces tenant isolation - users can only access data from their own tenant';

-- ============================================================================
-- INVITATIONS TABLE RLS
-- ============================================================================

ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;

-- Policy: Invitations scoped to tenant
CREATE POLICY tenant_isolation_invitations ON invitations
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

COMMENT ON POLICY tenant_isolation_invitations ON invitations IS 
    'Enforces tenant isolation for invitations';

-- ============================================================================
-- ROLES TABLE RLS
-- ============================================================================

ALTER TABLE roles ENABLE ROW LEVEL SECURITY;

-- Policy: Roles scoped to tenant
CREATE POLICY tenant_isolation_roles ON roles
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

COMMENT ON POLICY tenant_isolation_roles ON roles IS 
    'Enforces tenant isolation for roles';

-- ============================================================================
-- FARMERS TABLE RLS
-- ============================================================================

ALTER TABLE farmers ENABLE ROW LEVEL SECURITY;

-- Policy: Farmers scoped to tenant
CREATE POLICY tenant_isolation_farmers ON farmers
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

COMMENT ON POLICY tenant_isolation_farmers ON farmers IS 
    'Enforces tenant isolation for farmers';

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
