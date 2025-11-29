-- Migration 010: Move Platform Tables to Platform Schema
-- Moves all platform-related tables from public schema to platform schema

-- Move platform tables to platform schema
ALTER TABLE IF EXISTS platform_tenant SET SCHEMA platform;
ALTER TABLE IF EXISTS platform_users SET SCHEMA platform;
ALTER TABLE IF EXISTS platform_roles SET SCHEMA platform;
ALTER TABLE IF EXISTS platform_audit_log SET SCHEMA platform;

-- Verify tables moved
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'platform' AND table_name = 'platform_tenant'
    ) THEN
        RAISE EXCEPTION 'Table platform_tenant not in platform schema';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'platform' AND table_name = 'platform_users'
    ) THEN
        RAISE EXCEPTION 'Table platform_users not in platform schema';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'platform' AND table_name = 'platform_roles'
    ) THEN
        RAISE EXCEPTION 'Table platform_roles not in platform schema';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'platform' AND table_name = 'platform_audit_log'
    ) THEN
        RAISE EXCEPTION 'Table platform_audit_log not in platform schema';
    END IF;
    
    RAISE NOTICE 'All platform tables moved successfully';
END $$;
