-- Migration: 011_fix_invitation_rls.sql
-- Purpose: Add explicit INSERT policy for workspace invitations to prevent 500 errors
-- blocked by complex workspace membership checks or RLS constraints.

CREATE POLICY invitations_insert_sender ON b2c.workspace_invitations
    FOR INSERT
    WITH CHECK (
        invited_by = NULLIF(current_setting('app.current_user_id', true), '')::uuid
    );

-- Grant permissions just in case
DO $$
DECLARE
    _user text := current_setting('saas.app_db_user', true);
BEGIN
    IF _user IS NOT NULL AND _user != '' THEN
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON b2c.workspace_invitations TO %I', _user);
    END IF;
END $$;
