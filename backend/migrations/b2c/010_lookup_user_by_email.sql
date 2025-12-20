-- Migration: Add lookup_user_by_email function
-- This allows services to check for user existence by email without exposing the users table via RLS

CREATE OR REPLACE FUNCTION b2c.lookup_user_by_email(email_addr TEXT)
RETURNS UUID
SECURITY DEFINER
SET search_path = b2c, public
AS $$
BEGIN
    RETURN (SELECT id FROM b2c.users WHERE email = email_addr);
END;
$$ LANGUAGE plpgsql;
