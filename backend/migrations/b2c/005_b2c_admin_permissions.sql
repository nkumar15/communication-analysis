-- ============================================================================
-- B2C ADMIN PERMISSIONS
-- ============================================================================
-- Grants platform admin "God Mode" access to B2C tables for support/verification.
-- Can be disabled by deleting this file.
-- ============================================================================

-- Function: Get Platform Stats
CREATE OR REPLACE FUNCTION b2c.get_platform_stats()
RETURNS TABLE (
    total_workspaces BIGINT,
    personal_workspaces BIGINT,
    team_workspaces BIGINT,
    total_users BIGINT
)
SECURITY DEFINER
SET search_path = b2c, public
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM b2c.workspaces WHERE deleted_at IS NULL)::BIGINT,
        (SELECT COUNT(*) FROM b2c.workspaces WHERE type = 'personal' AND deleted_at IS NULL)::BIGINT,
        (SELECT COUNT(*) FROM b2c.workspaces WHERE type = 'team' AND deleted_at IS NULL)::BIGINT,
        (SELECT COUNT(*) FROM b2c.users WHERE deleted_at IS NULL)::BIGINT;
END;
$$ LANGUAGE plpgsql;

-- Admin Bypass Policies
CREATE POLICY admin_all_users ON b2c.users USING (current_setting('app.is_platform_admin', true) = 'true');
CREATE POLICY admin_all_workspaces ON b2c.workspaces USING (current_setting('app.is_platform_admin', true) = 'true');
CREATE POLICY admin_all_workspace_members ON b2c.workspace_members USING (current_setting('app.is_platform_admin', true) = 'true');
CREATE POLICY admin_all_workspace_invitations ON b2c.workspace_invitations USING (current_setting('app.is_platform_admin', true) = 'true');

CREATE POLICY subscription_plans_all_admin ON b2c.subscription_plans
    FOR ALL
    USING (current_setting('app.is_platform_admin', true) = 'true')
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true');

CREATE POLICY invoices_all_admin ON b2c.invoices
    FOR ALL
    USING (current_setting('app.is_platform_admin', true) = 'true')
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true');

CREATE POLICY subscriptions_all_admin ON b2c.subscriptions
    FOR ALL
    USING (current_setting('app.is_platform_admin', true) = 'true')
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true');
