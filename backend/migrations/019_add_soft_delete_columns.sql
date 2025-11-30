-- Migration: Add soft delete columns
-- Description: Adds deleted_at column to tenants, users, and auth_providers tables

-- 1. B2B Tenants
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'b2b' AND table_name = 'tenants' AND column_name = 'deleted_at') THEN
        ALTER TABLE b2b.tenants ADD COLUMN deleted_at TIMESTAMPTZ DEFAULT NULL;
        CREATE INDEX idx_tenants_deleted_at ON b2b.tenants(deleted_at) WHERE deleted_at IS NULL;
        RAISE NOTICE 'Added deleted_at to b2b.tenants';
    END IF;
END $$;

-- 2. B2B Users
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'b2b' AND table_name = 'users' AND column_name = 'deleted_at') THEN
        ALTER TABLE b2b.users ADD COLUMN deleted_at TIMESTAMPTZ DEFAULT NULL;
        CREATE INDEX idx_users_deleted_at ON b2b.users(deleted_at) WHERE deleted_at IS NULL;
        RAISE NOTICE 'Added deleted_at to b2b.users';
    END IF;
END $$;

-- 3. B2B Auth Providers
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'b2b' AND table_name = 'auth_providers' AND column_name = 'deleted_at') THEN
        ALTER TABLE b2b.auth_providers ADD COLUMN deleted_at TIMESTAMPTZ DEFAULT NULL;
        CREATE INDEX idx_auth_providers_deleted_at ON b2b.auth_providers(deleted_at) WHERE deleted_at IS NULL;
        RAISE NOTICE 'Added deleted_at to b2b.auth_providers';
    END IF;
END $$;

-- 4. Platform Users
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'platform' AND table_name = 'platform_users' AND column_name = 'deleted_at') THEN
        ALTER TABLE platform.platform_users ADD COLUMN deleted_at TIMESTAMPTZ DEFAULT NULL;
        CREATE INDEX idx_platform_users_deleted_at ON platform.platform_users(deleted_at) WHERE deleted_at IS NULL;
        RAISE NOTICE 'Added deleted_at to platform.platform_users';
    END IF;
END $$;

-- 5. Platform Auth Providers
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'platform' AND table_name = 'auth_providers' AND column_name = 'deleted_at') THEN
        ALTER TABLE platform.auth_providers ADD COLUMN deleted_at TIMESTAMPTZ DEFAULT NULL;
        CREATE INDEX idx_platform_auth_providers_deleted_at ON platform.auth_providers(deleted_at) WHERE deleted_at IS NULL;
        RAISE NOTICE 'Added deleted_at to platform.auth_providers';
    END IF;
END $$;

-- Verification
DO $$
DECLARE
    missing_cols INTEGER := 0;
BEGIN
    SELECT COUNT(*) INTO missing_cols
    FROM information_schema.columns 
    WHERE column_name = 'deleted_at' 
    AND (
        (table_schema = 'b2b' AND table_name IN ('tenants', 'users', 'auth_providers')) OR
        (table_schema = 'platform' AND table_name IN ('platform_users', 'auth_providers'))
    );
    
    IF missing_cols < 5 THEN
        RAISE EXCEPTION 'Verification failed: Expected 5 tables to have deleted_at, found %', missing_cols;
    ELSE
        RAISE NOTICE 'Verification passed: All 5 tables have deleted_at column';
    END IF;
END $$;

-- Rollback Instructions
/*
ALTER TABLE b2b.tenants DROP COLUMN IF EXISTS deleted_at;
ALTER TABLE b2b.users DROP COLUMN IF EXISTS deleted_at;
ALTER TABLE b2b.auth_providers DROP COLUMN IF EXISTS deleted_at;
ALTER TABLE platform.platform_users DROP COLUMN IF EXISTS deleted_at;
ALTER TABLE platform.auth_providers DROP COLUMN IF EXISTS deleted_at;
*/
