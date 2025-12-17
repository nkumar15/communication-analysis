-- ============================================================================
-- B2C WORKSPACE INVITATIONS (WITH SOFT DELETE)
-- ============================================================================
-- Migration: 006_workspace_invitations.sql
-- Purpose: Add workspace_invitations table for team collaboration with soft delete
-- Spec Reference: docs/specifications/b2c/workspaces.md#L54-L65
-- ============================================================================

-- ============================================================================
-- WORKSPACE INVITATIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS b2c.workspace_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES b2c.workspaces(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    invitation_token VARCHAR(255) UNIQUE NOT NULL,
    invited_by UUID NOT NULL REFERENCES b2c.users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancelled_by UUID REFERENCES b2c.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE b2c.workspace_invitations IS 'Workspace invitations with soft delete support';
COMMENT ON COLUMN b2c.workspace_invitations.cancelled_at IS 'Soft delete timestamp for cancelled invitations';
COMMENT ON COLUMN b2c.workspace_invitations.cancelled_by IS 'User who cancelled the invitation';

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX idx_b2c_invitations_token ON b2c.workspace_invitations(invitation_token);
CREATE INDEX idx_b2c_invitations_workspace ON b2c.workspace_invitations(workspace_id);
CREATE INDEX idx_b2c_invitations_email ON b2c.workspace_invitations(email);
-- Only index active invitations (not accepted, not cancelled, not expired)
CREATE INDEX idx_b2c_invitations_active ON b2c.workspace_invitations(workspace_id, email) 
    WHERE accepted_at IS NULL AND cancelled_at IS NULL;
CREATE INDEX idx_b2c_invitations_expires ON b2c.workspace_invitations(expires_at) 
    WHERE accepted_at IS NULL AND cancelled_at IS NULL;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================
ALTER TABLE b2c.workspace_invitations ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see invitations to their email (including cancelled for history)
CREATE POLICY invitation_recipient_access ON b2c.workspace_invitations
    USING (
        email = (SELECT email FROM b2c.users WHERE id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
    );

-- Policy: Users can see invitations in workspaces they're members of (for admin management)
CREATE POLICY invitation_workspace_access ON b2c.workspace_invitations
    USING (
        workspace_id IN (SELECT b2c.get_user_workspace_ids(NULLIF(current_setting('app.current_user_id', true), '')::uuid))
    );

-- Grant permissions to app user (ensures RLS policies work)
DO $$
DECLARE
    _user text := current_setting('saas.app_db_user', true);
BEGIN
    IF _user IS NOT NULL AND _user != '' THEN
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON b2c.workspace_invitations TO %I', _user);
        RAISE NOTICE 'Granted permissions on b2c.workspace_invitations to %', _user;
    END IF;
END $$;

-- ============================================================================
-- HELPER FUNCTION: Clean up expired invitations (soft delete)
-- ============================================================================
CREATE OR REPLACE FUNCTION b2c.cleanup_expired_invitations()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = b2c, public
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Soft delete expired invitations that haven't been accepted or cancelled
    UPDATE b2c.workspace_invitations
    SET cancelled_at = NOW(),
        cancelled_by = NULL,  -- System cleanup
        updated_at = NOW()
    WHERE expires_at < NOW()
      AND accepted_at IS NULL
      AND cancelled_at IS NULL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

COMMENT ON FUNCTION b2c.cleanup_expired_invitations() IS 'Soft deletes expired invitations. Run daily via cron job. Returns count of expired invitations.';

-- Grant execute on cleanup function
DO $$
DECLARE
    _user text := current_setting('saas.app_db_user', true);
BEGIN
    IF _user IS NOT NULL AND _user != '' THEN
        EXECUTE format('GRANT EXECUTE ON FUNCTION b2c.cleanup_expired_invitations() TO %I', _user);
        RAISE NOTICE 'Granted EXECUTE on b2c.cleanup_expired_invitations() to %', _user;
    END IF;
END $$;
