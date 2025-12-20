-- ============================================================================
-- B2C USER VISIBILITY FOR WORKSPACE MEMBERS
-- ============================================================================
-- Allows users to see other users in their shared workspaces
-- ============================================================================

-- Add policy to allow workspace members to see each other
CREATE POLICY workspace_member_user_visibility ON b2c.users
    USING (
        id IN (
            SELECT wm.user_id 
            FROM b2c.workspace_members wm
            WHERE wm.workspace_id IN (
                SELECT b2c.get_user_workspace_ids(NULLIF(current_setting('app.current_user_id', true), '')::uuid)
            )
        )
    );
