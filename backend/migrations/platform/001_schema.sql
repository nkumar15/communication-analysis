-- Platform Migration 001: Create Platform Schema
-- Creates the platform schema for SaaS administration

CREATE SCHEMA IF NOT EXISTS platform;

-- Verify schema created
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'platform') THEN
        RAISE EXCEPTION 'Schema platform not created';
    END IF;
    RAISE NOTICE 'Platform schema created successfully';
END $$;
