-- Migration 011: Move B2B Tables to B2B Schema
-- Moves all B2B tenant-related tables from public schema to b2b schema

-- Move B2B tables to b2b schema
ALTER TABLE IF EXISTS tenants SET SCHEMA b2b;
ALTER TABLE IF EXISTS users SET SCHEMA b2b;
ALTER TABLE IF EXISTS invitations SET SCHEMA b2b;
ALTER TABLE IF EXISTS roles SET SCHEMA b2b;
ALTER TABLE IF EXISTS resources SET SCHEMA b2b;
ALTER TABLE IF EXISTS actions SET SCHEMA b2b;
ALTER TABLE IF EXISTS role_permissions SET SCHEMA b2b;

-- Verify tables moved
DO $$
DECLARE
    expected_tables TEXT[] := ARRAY[
        'tenants', 'users', 'invitations', 'roles', 
        'resources', 'actions', 'role_permissions'
    ];
    tbl_name TEXT;
BEGIN
    FOREACH tbl_name IN ARRAY expected_tables
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'b2b' AND table_name = tbl_name
        ) THEN
            RAISE EXCEPTION 'Table % not in b2b schema', tbl_name;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'All B2B tables moved successfully';
END $$;
