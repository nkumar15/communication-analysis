-- Migration: Remove oidc_provider_id column from tenant tables
-- Purpose: Complete migration to auth_providers table
-- Dependencies: Requires migrations 016 and 017 to be run first

-- ============================================================================
-- IMPORTANT: Prerequisites Check
-- ============================================================================
-- This migration assumes:
-- 1. auth_providers table exists in both b2b and platform schemas (migration 016, 017)
-- 2. Data has been migrated from oidc_provider_id to auth_providers table
-- 3. Application code has been updated to use auth_providers table

-- ============================================================================
-- STEP 1: Verify auth_providers tables exist
-- ============================================================================

DO $$
BEGIN
    -- Check b2b.auth_providers exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'b2b' AND table_name = 'auth_providers'
    ) THEN
        RAISE EXCEPTION 'b2b.auth_providers table does not exist. Run migration 016 first.';
    END IF;
    
    -- Check platform.auth_providers exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'platform' AND table_name = 'auth_providers'
    ) THEN
        RAISE EXCEPTION 'platform.auth_providers table does not exist. Run migration 017 first.';
    END IF;
    
    RAISE NOTICE 'Prerequisites check passed: auth_providers tables exist';
END $$;

-- ============================================================================
-- STEP 2: Verification - Check for unmigrated data
-- ============================================================================

DO $$
DECLARE
    b2b_unmigrated_count INT;
    platform_unmigrated_count INT;
BEGIN
    -- Check B2B tenants with oidc_provider_id but no auth_providers entry
    SELECT COUNT(*) INTO b2b_unmigrated_count
    FROM b2b.tenants t
    WHERE t.oidc_provider_id IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM b2b.auth_providers ap
        WHERE ap.tenant_id = t.id AND ap.provider_id = t.oidc_provider_id
    );
    
    -- Check Platform tenant with oidc_provider_id but no auth_providers entry
    SELECT COUNT(*) INTO platform_unmigrated_count
    FROM platform.platform_tenant pt
    WHERE pt.oidc_provider_id IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM platform.auth_providers ap
        WHERE ap.platform_tenant_id = pt.id AND ap.provider_id = pt.oidc_provider_id
    );
    
    IF b2b_unmigrated_count > 0 THEN
        RAISE WARNING '% B2B tenants have oidc_provider_id but no auth_providers entry', b2b_unmigrated_count;
    END IF;
    
    IF platform_unmigrated_count > 0 THEN
        RAISE WARNING '% Platform tenants have oidc_provider_id but no auth_providers entry', platform_unmigrated_count;
    END IF;
    
    IF b2b_unmigrated_count = 0 AND platform_unmigrated_count = 0 THEN
        RAISE NOTICE 'Data verification passed: All oidc_provider_id data has been migrated';
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Remove oidc_provider_id column from b2b.tenants
-- ============================================================================

DO $$
BEGIN
    ALTER TABLE b2b.tenants DROP COLUMN IF EXISTS oidc_provider_id;
    RAISE NOTICE 'Removed oidc_provider_id column from b2b.tenants';
END $$;

-- ============================================================================
-- STEP 4: Remove oidc_provider_id column from platform.platform_tenant
-- ============================================================================

DO $$
BEGIN
    ALTER TABLE platform.platform_tenant DROP COLUMN IF EXISTS oidc_provider_id;
    RAISE NOTICE 'Removed oidc_provider_id column from platform.platform_tenant';
END $$;

-- ============================================================================
-- STEP 5: Final verification
-- ============================================================================

DO $$
BEGIN
    -- Verify column removed from b2b.tenants
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'b2b' 
        AND table_name = 'tenants' 
        AND column_name = 'oidc_provider_id'
    ) THEN
        RAISE EXCEPTION 'Failed to remove oidc_provider_id from b2b.tenants';
    END IF;
    
    -- Verify column removed from platform.platform_tenant
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'platform' 
        AND table_name = 'platform_tenant' 
        AND column_name = 'oidc_provider_id'
    ) THEN
        RAISE EXCEPTION 'Failed to remove oidc_provider_id from platform.platform_tenant';
    END IF;
    
    RAISE NOTICE '✅ Migration complete: oidc_provider_id column removed from all tenant tables';
END $$;

-- ============================================================================
-- ROLLBACK INSTRUCTIONS
-- ============================================================================
-- If you need to rollback this migration:
--
-- ALTER TABLE b2b.tenants ADD COLUMN oidc_provider_id VARCHAR(255);
-- ALTER TABLE platform.platform_tenant ADD COLUMN oidc_provider_id VARCHAR(255);
--
-- Then repopulate from auth_providers:
--
-- UPDATE b2b.tenants t
-- SET oidc_provider_id = (
--     SELECT ap.provider_id 
--     FROM b2b.auth_providers ap 
--     WHERE ap.tenant_id = t.id AND ap.is_primary = true
--     LIMIT 1
-- );
--
-- UPDATE platform.platform_tenant pt
-- SET oidc_provider_id = (
--     SELECT ap.provider_id 
--     FROM platform.auth_providers ap 
--     WHERE ap.platform_tenant_id = pt.id AND ap.is_primary = true
--     LIMIT 1
-- );
-- ============================================================================
