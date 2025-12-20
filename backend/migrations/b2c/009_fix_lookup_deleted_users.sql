-- Migration: Fix lookup_user_by_firebase_uid to allow finding deleted users
-- The middleware needs to find deleted users to return proper 404 responses

CREATE OR REPLACE FUNCTION b2c.lookup_user_by_firebase_uid(f_uid TEXT)
RETURNS UUID
SECURITY DEFINER
SET search_path = b2c, public
AS $$
BEGIN
    -- Return user ID even if deleted - middleware will check deleted_at
    RETURN (SELECT id FROM b2c.users WHERE firebase_uid = f_uid);
END;
$$ LANGUAGE plpgsql;
