-- ============================================================================
-- ENABLE RLS ON B2B SCHEMA (Private Data Only)
-- ============================================================================

-- NOTE: Tenants and Auth Providers are EXCLUDED from RLS.
-- They are required for unauthenticated "Resolve Tenant" flows.

-- 1. Enable RLS on Private Tables
ALTER TABLE b2b.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.team_members ENABLE ROW LEVEL SECURITY;

-- 2. Define Policies

-- ============================================================================
-- USERS
-- ============================================================================
-- Strict Tenant Isolation.
-- Middleware must set app.current_tenant_id BEFORE querying users.
DROP POLICY IF EXISTS user_isolation_policy ON b2b.users;
CREATE POLICY user_isolation_policy ON b2b.users
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

COMMENT ON POLICY user_isolation_policy ON b2b.users IS 
    'Enforces tenant isolation for users (domain-specific table)';

-- ============================================================================
-- TEAMS
-- ============================================================================
DROP POLICY IF EXISTS team_isolation_policy ON b2b.teams;
CREATE POLICY team_isolation_policy ON b2b.teams
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

COMMENT ON POLICY team_isolation_policy ON b2b.teams IS 
    'Enforces tenant isolation for teams (domain-specific table)';

-- ============================================================================
-- TEAM MEMBERS
-- ============================================================================
-- Check via team ownership
DROP POLICY IF EXISTS team_member_isolation_policy ON b2b.team_members;
CREATE POLICY team_member_isolation_policy ON b2b.team_members
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        team_id IN (
            SELECT id FROM b2b.teams 
            WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    );

COMMENT ON POLICY team_member_isolation_policy ON b2b.team_members IS 
    'Enforces tenant isolation for team members (domain-specific table)';
-- ============================================================================
-- ROLES
-- ============================================================================
DROP POLICY IF EXISTS role_isolation_policy ON b2b.roles;
CREATE POLICY role_isolation_policy ON b2b.roles
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
-- ============================================================================
-- ROLE PERMISSIONS
-- ============================================================================
-- Check via role ownership
DROP POLICY IF EXISTS role_permission_isolation_policy ON b2b.role_permissions;
CREATE POLICY role_permission_isolation_policy ON b2b.role_permissions
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        role_id IN (
            SELECT id FROM b2b.roles
            WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    );

COMMENT ON POLICY role_permission_isolation_policy ON b2b.role_permissions IS 
    'Enforces tenant isolation for role permissions (domain-specific table)';

-- ============================================================================
-- INVITATIONS
-- ============================================================================
DROP POLICY IF EXISTS invitation_isolation_policy ON b2b.invitations;
CREATE POLICY invitation_isolation_policy ON b2b.invitations
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

COMMENT ON POLICY invitation_isolation_policy ON b2b.invitations IS 
    'Enforces tenant isolation for invitations (domain-specific table)';
