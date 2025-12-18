-- Create b2b.subscription_plans table
CREATE TABLE IF NOT EXISTS b2b.subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier_key VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Pricing
    base_price_monthly INTEGER DEFAULT 0,
    base_price_yearly INTEGER DEFAULT 0,
    per_seat_price_monthly INTEGER DEFAULT 0,
    per_seat_price_yearly INTEGER DEFAULT 0,
    
    -- Features & Limits
    limits JSONB DEFAULT '{}',
    features JSONB DEFAULT '{}',
    
    -- Provider Config
    provider_config JSONB DEFAULT '{}',
    
    -- UI Flags
    contact_required BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    effective_from TIMESTAMPTZ DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_b2b_subscription_plans_tier_key ON b2b.subscription_plans(tier_key);
CREATE INDEX IF NOT EXISTS idx_b2b_subscription_plans_effective_from ON b2b.subscription_plans(effective_from);

COMMENT ON TABLE b2b.subscription_plans IS 'Catalog of B2B subscription plans with pricing and feature configuration';

-- Add plan_id to b2b.subscriptions
ALTER TABLE b2b.subscriptions 
ADD COLUMN IF NOT EXISTS plan_id UUID REFERENCES b2b.subscription_plans(id);

CREATE INDEX IF NOT EXISTS idx_b2b_subscriptions_plan_id ON b2b.subscriptions(plan_id);

-- Add plan_id to b2b.payment_mode_requests
ALTER TABLE b2b.payment_mode_requests 
ADD COLUMN IF NOT EXISTS plan_id UUID REFERENCES b2b.subscription_plans(id);

CREATE INDEX IF NOT EXISTS idx_b2b_payment_mode_requests_plan_id ON b2b.payment_mode_requests(plan_id);
