-- ============================================================================
-- B2C BILLING PROFILE
-- ============================================================================
-- Adds billing profile fields to B2C Users.
-- ============================================================================

ALTER TABLE b2c.users
ADD COLUMN IF NOT EXISTS tax_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS vat_number VARCHAR(50),
ADD COLUMN IF NOT EXISTS billing_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS billing_address JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS compliance_settings JSONB DEFAULT '{}'::jsonb;
