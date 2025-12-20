-- ============================================================================
-- B2C INVITATIONS
-- ============================================================================
-- Viral growth layer. Requires 001_b2c_core.sql
-- ============================================================================

-- TABLE
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

CREATE INDEX idx_b2c_invitations_token ON b2c.workspace_invitations(invitation_token);
CREATE INDEX idx_b2c_invitations_workspace ON b2c.workspace_invitations(workspace_id);
CREATE INDEX idx_b2c_invitations_email ON b2c.workspace_invitations(email);
CREATE INDEX idx_b2c_invitations_active ON b2c.workspace_invitations(workspace_id, email) 
    WHERE accepted_at IS NULL AND cancelled_at IS NULL;

-- HELPER FUNCTION: Cleanup Expired Invitations
CREATE OR REPLACE FUNCTION b2c.cleanup_expired_invitations()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = b2c, public
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    UPDATE b2c.workspace_invitations
    SET cancelled_at = NOW(),
        cancelled_by = NULL,
        updated_at = NOW()
    WHERE expires_at < NOW()
      AND accepted_at IS NULL
      AND cancelled_at IS NULL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

-- Grant permissions for app user to cleanup
DO $$
DECLARE
    _user text := current_setting('saas.app_db_user', true);
BEGIN
    IF _user IS NOT NULL AND _user != '' THEN
        EXECUTE format('GRANT EXECUTE ON FUNCTION b2c.cleanup_expired_invitations() TO %I', _user);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON b2c.workspace_invitations TO %I', _user);
    END IF;
END $$;

-- RLS POLICIES
ALTER TABLE b2c.workspace_invitations ENABLE ROW LEVEL SECURITY;

CREATE POLICY invitation_recipient_access ON b2c.workspace_invitations
    USING (
        email = (SELECT email FROM b2c.users WHERE id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
    );

CREATE POLICY invitation_workspace_access ON b2c.workspace_invitations
    USING (
        workspace_id IN (SELECT b2c.get_user_workspace_ids(NULLIF(current_setting('app.current_user_id', true), '')::uuid))
    );

CREATE POLICY invitations_insert_sender ON b2c.workspace_invitations
    FOR INSERT
    WITH CHECK (
        invited_by = NULLIF(current_setting('app.current_user_id', true), '')::uuid
    );
