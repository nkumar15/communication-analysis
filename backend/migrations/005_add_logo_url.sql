-- ============================================================================
-- Add logo_url to tenants
-- ============================================================================

ALTER TABLE b2b.tenants ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500);
COMMENT ON COLUMN b2b.tenants.logo_url IS 'URL to tenant logo image';
