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
CREATE POLICY user_isolation_policy ON b2b.users
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- ============================================================================
-- TEAMS
-- ============================================================================
CREATE POLICY team_isolation_policy ON b2b.teams
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- ============================================================================
-- TEAM MEMBERS
-- ============================================================================
-- Check via team ownership
CREATE POLICY team_member_isolation_policy ON b2b.team_members
    USING (
        team_id IN (
            SELECT id FROM b2b.teams 
            WHERE tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
    );

-- ============================================================================
-- ROLES
-- ============================================================================
CREATE POLICY role_isolation_policy ON b2b.roles
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- ============================================================================
-- ROLE PERMISSIONS
-- ============================================================================
-- Check via role ownership
CREATE POLICY role_permission_isolation_policy ON b2b.role_permissions
    USING (
        role_id IN (
            SELECT id FROM b2b.roles
            WHERE tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
    );

-- ============================================================================
-- INVITATIONS
-- ============================================================================
CREATE POLICY invitation_isolation_policy ON b2b.invitations
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
