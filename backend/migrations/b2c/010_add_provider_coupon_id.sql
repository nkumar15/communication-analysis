-- ============================================================================
-- B2C BILLING: COUPON PROVIDER ID
-- ============================================================================
-- Add Stripe coupon ID reference to coupons table
-- ============================================================================

-- Add provider_coupon_id to B2C coupons table
ALTER TABLE b2c.coupons ADD COLUMN IF NOT EXISTS provider_coupon_id VARCHAR(255);
