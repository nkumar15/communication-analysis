-- B2B Migration 001: Create B2B Schema
-- Creates the b2b schema for enterprise multi-tenant features

CREATE SCHEMA IF NOT EXISTS b2b;

-- Also create domain schema for B2B domain features (projects, tasks)
CREATE SCHEMA IF NOT EXISTS domain;

-- Verify schemas created
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'b2b') THEN
        RAISE EXCEPTION 'Schema b2b not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'domain') THEN
        RAISE EXCEPTION 'Schema domain not created';
    END IF;
    RAISE NOTICE 'B2B and domain schemas created successfully';
END $$;
