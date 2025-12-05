-- ============================================================================
-- UPDATE RLS POLICIES FOR PLATFORM ADMIN & ROBUSTNESS
-- ============================================================================

-- 1. USERS
DROP POLICY IF EXISTS user_isolation_policy ON b2b.users;
CREATE POLICY user_isolation_policy ON b2b.users
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- 2. TEAMS
DROP POLICY IF EXISTS team_isolation_policy ON b2b.teams;
CREATE POLICY team_isolation_policy ON b2b.teams
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- 3. TEAM MEMBERS
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

-- 4. ROLES
DROP POLICY IF EXISTS role_isolation_policy ON b2b.roles;
CREATE POLICY role_isolation_policy ON b2b.roles
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- 5. ROLE PERMISSIONS
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

-- 6. INVITATIONS
DROP POLICY IF EXISTS invitation_isolation_policy ON b2b.invitations;
CREATE POLICY invitation_isolation_policy ON b2b.invitations
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
