-- B2C Migration 001: Create B2C Schema
-- Creates the b2c schema for personal/team workspaces

CREATE SCHEMA IF NOT EXISTS b2c;

-- Verify schema created
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'b2c') THEN
        RAISE EXCEPTION 'Schema b2c not created';
    END IF;
    RAISE NOTICE 'B2C schema created successfully';
END $$;
