-- Migration 012: Move Domain Tables to Domain Schemas
-- Moves domain-specific tables from public schema to their respective domain schemas

-- Move farming domain tables
ALTER TABLE IF EXISTS farmers SET SCHEMA farming;

-- Verify tables moved
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'farming' AND table_name = 'farmers'
    ) THEN
        RAISE EXCEPTION 'Table farmers not in farming schema';
    END IF;
    
    RAISE NOTICE 'All domain tables moved successfully';
END $$;
