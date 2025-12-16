-- ============================================================================
-- B2C Platform Admin Functions
-- ============================================================================
-- Functions to bypass RLS for platform admin statistics and management
-- ============================================================================

-- Function to get B2C statistics (bypasses RLS)
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