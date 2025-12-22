-- Add provider_coupon_id to B2B coupons table
ALTER TABLE b2b.coupons ADD COLUMN IF NOT EXISTS provider_coupon_id VARCHAR(255);
