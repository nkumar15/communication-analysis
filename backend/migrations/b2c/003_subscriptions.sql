-- B2C Subscriptions & Billing Schema
-- Migration: 003_subscriptions.sql
-- Description: Tables for subscription management, payment methods, invoices, and coupons

-- ============================================================================
-- SUBSCRIPTIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2c.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID UNIQUE REFERENCES b2c.workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES b2c.users(id) ON DELETE CASCADE,
    
    -- Plan Link (Grandfathering support)
    plan_id UUID REFERENCES b2c.subscription_plans(id),
    
    -- Provider Info (for multi-provider support)
    provider VARCHAR(50) NOT NULL DEFAULT 'stripe', -- 'stripe' | 'razorpay' | 'xendit'
    provider_customer_id VARCHAR(255),
    provider_subscription_id VARCHAR(255) UNIQUE,
    
    -- Plan Details (Derived from plan_id usually, but kept for historical/custom overrides if needed)
    billing_interval VARCHAR(20) DEFAULT 'monthly', -- 'monthly' | 'yearly'
    
    -- Status
    status VARCHAR(50) DEFAULT 'active', -- 'active' | 'canceled' | 'past_due' | 'trialing'
    trial_ends_at TIMESTAMPTZ,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT false,
    canceled_at TIMESTAMPTZ,
    
    -- Pricing
    amount_cents INTEGER DEFAULT 0, -- Price in cents
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete')),
    CONSTRAINT valid_interval CHECK (billing_interval IN ('monthly', 'yearly'))
);

CREATE INDEX idx_subscriptions_workspace ON b2c.subscriptions(workspace_id);
CREATE INDEX idx_subscriptions_user ON b2c.subscriptions(user_id);
CREATE INDEX idx_subscriptions_provider_id ON b2c.subscriptions(provider_subscription_id);
CREATE INDEX idx_subscriptions_status ON b2c.subscriptions(status);

-- ============================================================================
-- PAYMENT METHODS
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2c.payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES b2c.users(id) ON DELETE CASCADE,
    
    -- Provider Info
    provider VARCHAR(50) NOT NULL DEFAULT 'stripe',
    provider_payment_method_id VARCHAR(255) UNIQUE,
    provider_customer_id VARCHAR(255),
    
    -- Card Details (for display purposes)
    type VARCHAR(50), -- 'card' | 'bank_account' | 'wallet'
    card_brand VARCHAR(50), -- 'visa' | 'mastercard' | 'amex'
    card_last4 VARCHAR(4),
    card_exp_month INTEGER,
    card_exp_year INTEGER,
    
    -- Metadata
    is_default BOOLEAN DEFAULT false,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payment_methods_user ON b2c.payment_methods(user_id);
CREATE INDEX idx_payment_methods_provider_id ON b2c.payment_methods(provider_payment_method_id);

-- ============================================================================
-- INVOICES
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2c.invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES b2c.subscriptions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES b2c.users(id) ON DELETE CASCADE,
    
    -- Provider Info
    provider VARCHAR(50) NOT NULL DEFAULT 'stripe',
    provider_invoice_id VARCHAR(255) UNIQUE,
    
    -- Invoice Details
    amount_due INTEGER NOT NULL, -- in cents
    amount_paid INTEGER DEFAULT 0, -- in cents
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'draft', -- 'draft' | 'open' | 'paid' | 'void' | 'uncollectible'
    
    -- URLs
    invoice_pdf_url TEXT,
    hosted_invoice_url TEXT,
    
    -- Dates
    invoice_date TIMESTAMPTZ,
    due_date TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_invoice_status CHECK (status IN ('draft', 'open', 'paid', 'void', 'uncollectible'))
);

CREATE INDEX idx_invoices_subscription ON b2c.invoices(subscription_id);
CREATE INDEX idx_invoices_user ON b2c.invoices(user_id);
CREATE INDEX idx_invoices_provider_id ON b2c.invoices(provider_invoice_id);
CREATE INDEX idx_invoices_status ON b2c.invoices(status);

-- ============================================================================
-- SUBSCRIPTION EVENTS (Audit Trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2c.subscription_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES b2c.subscriptions(id) ON DELETE CASCADE,
    
    -- Event Details
    event_type VARCHAR(100) NOT NULL, -- e.g., 'subscription.created', 'subscription.updated'
    provider VARCHAR(50) NOT NULL DEFAULT 'stripe',
    provider_event_id VARCHAR(255),
    
    -- Payload
    payload JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscription_events_subscription ON b2c.subscription_events(subscription_id);
CREATE INDEX idx_subscription_events_type ON b2c.subscription_events(event_type);
CREATE INDEX idx_subscription_events_created ON b2c.subscription_events(created_at DESC);

-- ============================================================================
-- COUPONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2c.coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Coupon Details
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    
    -- Discount
    discount_type VARCHAR(20) NOT NULL, -- 'percentage' | 'fixed_amount'
    discount_percent INTEGER, -- 0-100 for percentage discounts
    discount_amount_cents INTEGER, -- for fixed amount discounts
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Usage Limits
    max_redemptions INTEGER, -- NULL = unlimited
    times_redeemed INTEGER DEFAULT 0,
    
    -- Validity
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    
    -- Applicable Tiers (NULL = all tiers)
    applicable_tiers TEXT[], -- ['premium', 'ultimate']
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_discount_type CHECK (discount_type IN ('percentage', 'fixed_amount')),
    CONSTRAINT valid_discount_percent CHECK (discount_percent IS NULL OR (discount_percent >= 0 AND discount_percent <= 100))
);

CREATE INDEX idx_coupons_code ON b2c.coupons(code);
CREATE INDEX idx_coupons_active ON b2c.coupons(is_active);

-- ============================================================================
-- COUPON REDEMPTIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2c.coupon_redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_id UUID REFERENCES b2c.coupons(id) ON DELETE CASCADE,
    user_id UUID REFERENCES b2c.users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES b2c.subscriptions(id) ON DELETE SET NULL,
    
    -- Discount Applied
    discount_amount_cents INTEGER,
    
    -- Timestamps
    redeemed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Uniqueness: one redemption per user per coupon
    UNIQUE(coupon_id, user_id)
);

CREATE INDEX idx_coupon_redemptions_coupon ON b2c.coupon_redemptions(coupon_id);
CREATE INDEX idx_coupon_redemptions_user ON b2c.coupon_redemptions(user_id);

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

-- Subscriptions: Users can view their own subscription
ALTER TABLE b2c.subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY subscriptions_select_own ON b2c.subscriptions
    FOR SELECT
    USING (user_id::TEXT = current_setting('app.current_user_id', true));

-- Payment Methods: Users can manage their own payment methods
ALTER TABLE b2c.payment_methods ENABLE ROW LEVEL SECURITY;

CREATE POLICY payment_methods_select_own ON b2c.payment_methods
    FOR SELECT
    USING (user_id::TEXT = current_setting('app.current_user_id', true));

CREATE POLICY payment_methods_insert_own ON b2c.payment_methods
    FOR INSERT
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));

CREATE POLICY payment_methods_delete_own ON b2c.payment_methods
    FOR DELETE
    USING (user_id::TEXT = current_setting('app.current_user_id', true));

-- Invoices: Users can view their own invoices
ALTER TABLE b2c.invoices ENABLE ROW LEVEL SECURITY;

CREATE POLICY invoices_select_own ON b2c.invoices
    FOR SELECT
    USING (user_id::TEXT = current_setting('app.current_user_id', true));

-- Subscription Events: Read-only audit trail
ALTER TABLE b2c.subscription_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY subscription_events_select_own ON b2c.subscription_events
    FOR SELECT
    USING (
        subscription_id IN (
            SELECT id FROM b2c.subscriptions
            WHERE user_id::TEXT = current_setting('app.current_user_id', true)
        )
    );

-- Coupons: Public read (for validation)
ALTER TABLE b2c.coupons ENABLE ROW LEVEL SECURITY;

CREATE POLICY coupons_select_all ON b2c.coupons
    FOR SELECT
    USING (is_active = true AND (valid_until IS NULL OR valid_until > NOW()));

-- Coupon Redemptions: Users can view their own redemptions
ALTER TABLE b2c.coupon_redemptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY coupon_redemptions_select_own ON b2c.coupon_redemptions
    FOR SELECT
    USING (user_id::TEXT = current_setting('app.current_user_id', true));

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION b2c.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON b2c.subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION b2c.update_updated_at_column();

CREATE TRIGGER update_payment_methods_updated_at
    BEFORE UPDATE ON b2c.payment_methods
    FOR EACH ROW
    EXECUTE FUNCTION b2c.update_updated_at_column();

CREATE TRIGGER update_invoices_updated_at
    BEFORE UPDATE ON b2c.invoices
    FOR EACH ROW
    EXECUTE FUNCTION b2c.update_updated_at_column();

CREATE TRIGGER update_coupons_updated_at
    BEFORE UPDATE ON b2c.coupons
    FOR EACH ROW
    EXECUTE FUNCTION b2c.update_updated_at_column();

-- ============================================================================
-- SEED DATA: Free Tier for Existing Users
-- ============================================================================

-- Create free tier subscriptions for all existing workspaces without a subscription
-- Create free tier subscriptions for all existing workspaces without a subscription
-- NOTE: We insert with NULL plan_id initially. The application assumes NULL plan_id + status 'active' = Legacy Free or Default Free.
-- Ideally proper seeding happens via scripts.
INSERT INTO b2c.subscriptions (workspace_id, user_id, status, amount_cents)
SELECT 
    w.id,
    w.owner_id,
    'active',
    0
FROM b2c.workspaces w
WHERE NOT EXISTS (
    SELECT 1 FROM b2c.subscriptions s WHERE s.workspace_id = w.id
);
