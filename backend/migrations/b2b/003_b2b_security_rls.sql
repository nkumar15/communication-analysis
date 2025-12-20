-- ============================================================================
-- B2B RLS POLICIES
-- ============================================================================
-- Enforce Multi-Tenancy on all tables.
-- ============================================================================

-- VALIDATION:
-- Tenants, Auth Providers, Resources, Actions, Role Templates are EXCLUDED from RLS.
-- Resources/Actions/Templates are global/public reference data.

-- 1. Enable RLS
ALTER TABLE b2b.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.team_role_definitions ENABLE ROW LEVEL SECURITY;

-- 2. Define Policies

-- USERS
DROP POLICY IF EXISTS user_isolation_policy ON b2b.users;
CREATE POLICY user_isolation_policy ON b2b.users
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- TEAMS
DROP POLICY IF EXISTS team_isolation_policy ON b2b.teams;
CREATE POLICY team_isolation_policy ON b2b.teams
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- TEAM MEMBERS
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

-- ROLES
DROP POLICY IF EXISTS role_isolation_policy ON b2b.roles;
CREATE POLICY role_isolation_policy ON b2b.roles
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- ROLE PERMISSIONS (via Role)
-- Ensure users can only see permissions for roles in their tenant
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

-- INVITATIONS
DROP POLICY IF EXISTS invitation_isolation_policy ON b2b.invitations;
CREATE POLICY invitation_isolation_policy ON b2b.invitations
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- TEAM ROLE DEFINITIONS
-- Read: System roles (tenant_id IS NULL) + Tenant-specific roles
-- Write: Tenant-specific roles only (implied by tenant_id column existence usually, but RLS checks rows)
DROP POLICY IF EXISTS team_role_definitions_policy ON b2b.team_role_definitions;
CREATE POLICY team_role_definitions_policy ON b2b.team_role_definitions
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id IS NULL 
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
