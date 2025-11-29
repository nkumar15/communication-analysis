-- Migration 009: Create Database Schemas
-- Creates separate schemas for platform, b2b, b2c, and domains
-- Migration tracking table remains in public schema

-- Create schemas
CREATE SCHEMA IF NOT EXISTS platform;
CREATE SCHEMA IF NOT EXISTS b2b;
CREATE SCHEMA IF NOT EXISTS b2c;
CREATE SCHEMA IF NOT EXISTS farming;

-- Verify schemas created
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'platform') THEN
        RAISE EXCEPTION 'Schema platform not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'b2b') THEN
        RAISE EXCEPTION 'Schema b2b not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'b2c') THEN
        RAISE EXCEPTION 'Schema b2c not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'farming') THEN
        RAISE EXCEPTION 'Schema farming not created';
    END IF;
    
    RAISE NOTICE 'All schemas created successfully';
END $$;
