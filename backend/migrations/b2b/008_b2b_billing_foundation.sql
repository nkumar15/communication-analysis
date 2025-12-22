-- ============================================================================
-- B2B BILLING FOUNDATION
-- ============================================================================
-- Adds support for Coupons and comprehensive Billing Profiles for Tenants.
-- ============================================================================

-- 1. TENANT BILLING PROFILE
-- Add fields to store tax and compliance info
ALTER TABLE b2b.tenants 
ADD COLUMN IF NOT EXISTS tax_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS vat_number VARCHAR(50),
ADD COLUMN IF NOT EXISTS billing_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS billing_address JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS compliance_settings JSONB DEFAULT '{}'::jsonb;

-- 2. B2B COUPONS
CREATE TABLE IF NOT EXISTS b2b.coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL, -- 'percentage', 'fixed_amount'
    discount_percent INTEGER,
    discount_amount_cents INTEGER,
    currency VARCHAR(3) DEFAULT 'USD',
    max_redemptions INTEGER,
    times_redeemed INTEGER DEFAULT 0,
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    applicable_tiers TEXT[], -- 'starter', 'professional', etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trigger for updated_at (Use correct function name)
DROP TRIGGER IF EXISTS update_b2b_coupons_updated_at ON b2b.coupons;
CREATE TRIGGER update_b2b_coupons_updated_at
    BEFORE UPDATE ON b2b.coupons
    FOR EACH ROW EXECUTE FUNCTION b2b.update_timestamp_column();

-- 3. B2B COUPON REDEMPTIONS
CREATE TABLE IF NOT EXISTS b2b.coupon_redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_id UUID REFERENCES b2b.coupons(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES b2b.subscriptions(id) ON DELETE SET NULL,
    discount_amount_cents INTEGER,
    redeemed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    redeemed_by UUID, -- User who applied it
    UNIQUE(coupon_id, tenant_id) -- One redemption per coupon per tenant
);

-- 4. RLS POLICIES

-- Enable RLS
ALTER TABLE b2b.coupons ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.coupon_redemptions ENABLE ROW LEVEL SECURITY;

-- Coupons: Public Read (if active) OR Admin All
DROP POLICY IF EXISTS coupons_select_all ON b2b.coupons;
CREATE POLICY coupons_select_all ON b2b.coupons
    FOR SELECT
    USING (
        (is_active = true AND (valid_until IS NULL OR valid_until > NOW()))
        OR 
        (current_setting('app.is_platform_admin', true) = 'true')
    );

DROP POLICY IF EXISTS coupons_admin_all ON b2b.coupons;
CREATE POLICY coupons_admin_all ON b2b.coupons
    FOR ALL
    USING (current_setting('app.is_platform_admin', true) = 'true')
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true');

-- Redemptions: Tenant Read/Insert
DROP POLICY IF EXISTS coupon_redemptions_tenant_access ON b2b.coupon_redemptions;
CREATE POLICY coupon_redemptions_tenant_access ON b2b.coupon_redemptions
    FOR SELECT
    USING (
        tenant_id::TEXT = current_setting('app.current_tenant_id', true)
    );

DROP POLICY IF EXISTS coupon_redemptions_admin_all ON b2b.coupon_redemptions;
CREATE POLICY coupon_redemptions_admin_all ON b2b.coupon_redemptions
    FOR ALL
    USING (current_setting('app.is_platform_admin', true) = 'true');
