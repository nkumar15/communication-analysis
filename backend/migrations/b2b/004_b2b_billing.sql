-- ============================================================================
-- B2B BILLING SCHEMA
-- ============================================================================
-- Subscription Plans, Subscriptions, Invoices, Payment Requests
-- ============================================================================

-- TYPES
DO $$ BEGIN
    CREATE TYPE b2b.subscription_tier AS ENUM ('starter', 'professional', 'enterprise');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE b2b.payment_mode AS ENUM ('card', 'invoice');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE b2b.invoice_status AS ENUM ('draft', 'pending_approval', 'approved', 'sent', 'paid', 'overdue', 'void');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- 1. SUBSCRIPTION PLANS
CREATE TABLE IF NOT EXISTS b2b.subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier_key VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    base_price_monthly INTEGER DEFAULT 0,
    base_price_yearly INTEGER DEFAULT 0,
    per_seat_price_monthly INTEGER DEFAULT 0,
    per_seat_price_yearly INTEGER DEFAULT 0,
    limits JSONB DEFAULT '{}',
    features JSONB DEFAULT '{}',
    provider_config JSONB DEFAULT '{}',
    contact_required BOOLEAN DEFAULT FALSE,
    effective_from TIMESTAMPTZ DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_b2b_subscription_plans_tier_key ON b2b.subscription_plans(tier_key);

-- 2. SUBSCRIPTIONS
CREATE TABLE IF NOT EXISTS b2b.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID UNIQUE REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES b2b.subscription_plans(id),
    
    tier VARCHAR(50) NOT NULL DEFAULT 'starter',
    payment_mode VARCHAR(20) NOT NULL DEFAULT 'card',
    status VARCHAR(50) DEFAULT 'active',
    
    seat_count INTEGER NOT NULL DEFAULT 1,
    base_price_cents INTEGER NOT NULL DEFAULT 0,
    per_seat_price_cents INTEGER NOT NULL DEFAULT 0,
    total_amount_cents INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    billing_interval VARCHAR(20) DEFAULT 'monthly',
    
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    trial_ends_at TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT false,
    canceled_at TIMESTAMP WITH TIME ZONE,
    
    provider VARCHAR(50) NOT NULL DEFAULT 'stripe',
    provider_customer_id VARCHAR(255),
    provider_subscription_id VARCHAR(255) UNIQUE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_b2b_subscriptions_tenant ON b2b.subscriptions(tenant_id);

-- 3. INVOICES
CREATE TABLE IF NOT EXISTS b2b.invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES b2b.subscriptions(id) ON DELETE SET NULL,
    tenant_id UUID REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    provider VARCHAR(50) DEFAULT 'manual',
    provider_invoice_id VARCHAR(255) UNIQUE,
    status VARCHAR(50) DEFAULT 'draft',
    amount_due INTEGER NOT NULL,
    amount_paid INTEGER DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    
    seat_count_snapshot INTEGER NOT NULL,
    base_price_snapshot_cents INTEGER NOT NULL,
    per_seat_price_snapshot_cents INTEGER NOT NULL,
    
    billing_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    billing_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    invoice_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    due_date TIMESTAMP WITH TIME ZONE,
    paid_at TIMESTAMP WITH TIME ZONE,
    
    invoice_pdf_url TEXT,
    hosted_invoice_url TEXT,
    
    approved_by UUID,
    approved_at TIMESTAMP WITH TIME ZONE,
    marked_paid_by UUID,
    payment_notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. SUBSCRIPTION EVENTS
CREATE TABLE IF NOT EXISTS b2b.subscription_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES b2b.subscriptions(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    provider VARCHAR(50) DEFAULT 'system',
    provider_event_id VARCHAR(255),
    payload JSONB,
    triggered_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. PAYMENT MODE REQUESTS
CREATE TABLE IF NOT EXISTS b2b.payment_mode_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES b2b.subscriptions(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES b2b.subscription_plans(id),
    current_mode VARCHAR(20) NOT NULL,
    requested_mode VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    requested_by UUID REFERENCES b2b.users(id),
    request_reason TEXT,
    reviewed_by UUID,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    admin_notes TEXT,
    effective_date TIMESTAMP WITH TIME ZONE,
    applied_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS POLICIES FOR BILLING
ALTER TABLE b2b.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.subscription_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.payment_mode_requests ENABLE ROW LEVEL SECURITY;

-- Common policy: Tenant Isolation + Admin Bypass
CREATE POLICY subscriptions_tenant_isolation ON b2b.subscriptions
    USING (current_setting('app.is_platform_admin', true) = 'true' OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

CREATE POLICY invoices_tenant_isolation ON b2b.invoices
    USING (current_setting('app.is_platform_admin', true) = 'true' OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

CREATE POLICY subscription_events_tenant_isolation ON b2b.subscription_events
    USING (current_setting('app.is_platform_admin', true) = 'true' OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

CREATE POLICY payment_mode_requests_tenant_isolation ON b2b.payment_mode_requests
    USING (current_setting('app.is_platform_admin', true) = 'true' OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

-- TRIGGERS
CREATE OR REPLACE FUNCTION b2b.update_billing_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON b2b.subscriptions FOR EACH ROW EXECUTE FUNCTION b2b.update_billing_updated_at_column();
CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON b2b.invoices FOR EACH ROW EXECUTE FUNCTION b2b.update_billing_updated_at_column();
CREATE TRIGGER update_payment_mode_requests_updated_at BEFORE UPDATE ON b2b.payment_mode_requests FOR EACH ROW EXECUTE FUNCTION b2b.update_billing_updated_at_column();
