-- ============================================================================
-- B2C SUBSCRIPTIONS & BILLING
-- ============================================================================
-- Monetization layer. Plans, Payments, Invoices, Coupons.
-- ============================================================================

-- PLANS
CREATE TABLE b2c.subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    price_monthly INTEGER,
    price_yearly INTEGER,
    provider_config JSONB DEFAULT '{}'::jsonb,
    limits JSONB NOT NULL DEFAULT '{}'::jsonb,
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    effective_from TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    archived_at TIMESTAMP WITH TIME ZONE,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TRIGGER update_subscription_plans_updated_at
    BEFORE UPDATE ON b2c.subscription_plans
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- SUBSCRIPTIONS
CREATE TABLE IF NOT EXISTS b2c.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID UNIQUE REFERENCES b2c.workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES b2c.users(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES b2c.subscription_plans(id),
    provider VARCHAR(50) NOT NULL DEFAULT 'stripe',
    provider_customer_id VARCHAR(255),
    provider_subscription_id VARCHAR(255) UNIQUE,
    billing_interval VARCHAR(20) DEFAULT 'monthly',
    status VARCHAR(50) DEFAULT 'active',
    trial_ends_at TIMESTAMPTZ,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT false,
    canceled_at TIMESTAMPTZ,
    amount_cents INTEGER DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_status CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete')),
    CONSTRAINT valid_interval CHECK (billing_interval IN ('monthly', 'yearly'))
);

CREATE INDEX idx_subscriptions_workspace ON b2c.subscriptions(workspace_id);
CREATE INDEX idx_subscriptions_user ON b2c.subscriptions(user_id);
CREATE INDEX idx_subscriptions_provider_id ON b2c.subscriptions(provider_subscription_id);

CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON b2c.subscriptions
    FOR EACH ROW EXECUTE FUNCTION b2c.update_updated_at_column();

-- PAYMENT METHODS
CREATE TABLE IF NOT EXISTS b2c.payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES b2c.users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL DEFAULT 'stripe',
    provider_payment_method_id VARCHAR(255) UNIQUE,
    provider_customer_id VARCHAR(255),
    type VARCHAR(50),
    card_brand VARCHAR(50),
    card_last4 VARCHAR(4),
    card_exp_month INTEGER,
    card_exp_year INTEGER,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER update_payment_methods_updated_at
    BEFORE UPDATE ON b2c.payment_methods
    FOR EACH ROW EXECUTE FUNCTION b2c.update_updated_at_column();

-- INVOICES
CREATE TABLE IF NOT EXISTS b2c.invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES b2c.subscriptions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES b2c.users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL DEFAULT 'stripe',
    provider_invoice_id VARCHAR(255) UNIQUE,
    amount_due INTEGER NOT NULL,
    amount_paid INTEGER DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'draft',
    invoice_pdf_url TEXT,
    hosted_invoice_url TEXT,
    invoice_date TIMESTAMPTZ,
    due_date TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER update_invoices_updated_at
    BEFORE UPDATE ON b2c.invoices
    FOR EACH ROW EXECUTE FUNCTION b2c.update_updated_at_column();

-- SUBSCRIPTION EVENTS
CREATE TABLE IF NOT EXISTS b2c.subscription_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES b2c.subscriptions(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL DEFAULT 'stripe',
    provider_event_id VARCHAR(255),
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- COUPONS
CREATE TABLE IF NOT EXISTS b2c.coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL,
    discount_percent INTEGER,
    discount_amount_cents INTEGER,
    currency VARCHAR(3) DEFAULT 'USD',
    max_redemptions INTEGER,
    times_redeemed INTEGER DEFAULT 0,
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    applicable_tiers TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER update_coupons_updated_at
    BEFORE UPDATE ON b2c.coupons
    FOR EACH ROW EXECUTE FUNCTION b2c.update_updated_at_column();

-- COUPON REDEMPTIONS
CREATE TABLE IF NOT EXISTS b2c.coupon_redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_id UUID REFERENCES b2c.coupons(id) ON DELETE CASCADE,
    user_id UUID REFERENCES b2c.users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES b2c.subscriptions(id) ON DELETE SET NULL,
    discount_amount_cents INTEGER,
    redeemed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(coupon_id, user_id)
);

-- RLS POLICIES

-- ENABLE RLS
ALTER TABLE b2c.subscription_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2c.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2c.payment_methods ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2c.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2c.subscription_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2c.coupons ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2c.coupon_redemptions ENABLE ROW LEVEL SECURITY;

-- Plans: Public Read (Active) OR Admin All
CREATE POLICY subscription_plans_select_public ON b2c.subscription_plans
    FOR SELECT
    USING (
        (effective_from <= NOW() AND archived_at IS NULL)
        OR 
        (current_setting('app.is_platform_admin', true) = 'true')
    );

-- Subscriptions: Own Access
CREATE POLICY subscriptions_select_own ON b2c.subscriptions
    FOR SELECT
    USING (user_id::TEXT = current_setting('app.current_user_id', true));

CREATE POLICY subscriptions_insert_own ON b2c.subscriptions
    FOR INSERT
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));

CREATE POLICY subscriptions_update_own ON b2c.subscriptions
    FOR UPDATE
    USING (user_id::TEXT = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));

-- Payment Methods: Own Access
CREATE POLICY payment_methods_select_own ON b2c.payment_methods
    FOR SELECT
    USING (user_id::TEXT = current_setting('app.current_user_id', true));

CREATE POLICY payment_methods_insert_own ON b2c.payment_methods
    FOR INSERT
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));

CREATE POLICY payment_methods_update_own ON b2c.payment_methods
    FOR UPDATE
    USING (user_id::TEXT = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));

CREATE POLICY payment_methods_delete_own ON b2c.payment_methods
    FOR DELETE
    USING (user_id::TEXT = current_setting('app.current_user_id', true));

-- Invoices: Own Access
CREATE POLICY invoices_select_own ON b2c.invoices
    FOR SELECT
    USING (user_id::TEXT = current_setting('app.current_user_id', true));

CREATE POLICY invoices_insert_own ON b2c.invoices
    FOR INSERT
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));

CREATE POLICY invoices_update_own ON b2c.invoices
    FOR UPDATE
    USING (user_id::TEXT = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));

-- Events: Own Read
CREATE POLICY subscription_events_select_own ON b2c.subscription_events
    FOR SELECT
    USING (
        subscription_id IN (
            SELECT id FROM b2c.subscriptions
            WHERE user_id::TEXT = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY subscription_events_insert_own ON b2c.subscription_events
    FOR INSERT
    WITH CHECK (
        subscription_id IN (
            SELECT id FROM b2c.subscriptions
            WHERE user_id::TEXT = current_setting('app.current_user_id', true)
        )
    );

-- Coupons: Local Public Read / Admin All
CREATE POLICY coupons_select_all ON b2c.coupons
    FOR SELECT
    USING (is_active = true AND (valid_until IS NULL OR valid_until > NOW()));

CREATE POLICY coupons_insert_all ON b2c.coupons FOR INSERT WITH CHECK (true);
CREATE POLICY coupons_update_all ON b2c.coupons FOR UPDATE USING (true) WITH CHECK (true);

-- Redemptions: Own Access
CREATE POLICY coupon_redemptions_select_own ON b2c.coupon_redemptions
    FOR SELECT
    USING (user_id::TEXT = current_setting('app.current_user_id', true));

CREATE POLICY coupon_redemptions_insert_own ON b2c.coupon_redemptions
    FOR INSERT
    WITH CHECK (user_id::TEXT = current_setting('app.current_user_id', true));
