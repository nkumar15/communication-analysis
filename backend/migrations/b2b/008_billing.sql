-- B2B Billing & Subscriptions Schema
-- Migration: 008_billing.sql
-- Description: Tables for B2B subscription management, invoices, and payment mode approval workflow
--
-- Key Features:
--   - Tenant-level subscriptions with base + per-seat pricing
--   - Dual payment modes: Stripe card and invoice/wire transfer
--   - Platform admin approval workflow for payment mode changes
--   - Auto-generated monthly invoices with seat snapshots
--   - RLS policies using app.current_tenant_id

-- ============================================================================
-- SUBSCRIPTION TIERS ENUM
-- ============================================================================
-- Define valid subscription tiers for B2B
DO $$ BEGIN
    CREATE TYPE b2b.subscription_tier AS ENUM ('starter', 'professional', 'enterprise');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE b2b.payment_mode AS ENUM ('card', 'invoice');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE b2b.invoice_status AS ENUM ('draft', 'pending_approval', 'approved', 'sent', 'paid', 'overdue', 'void');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- SUBSCRIPTIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID UNIQUE REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    
    -- Subscription Details
    tier VARCHAR(50) NOT NULL DEFAULT 'starter', -- 'starter' | 'professional' | 'enterprise'
    payment_mode VARCHAR(20) NOT NULL DEFAULT 'card', -- 'card' | 'invoice'
    status VARCHAR(50) DEFAULT 'active', -- 'active' | 'canceled' | 'past_due' | 'trialing' | 'incomplete'
    
    -- Pricing (Base + Per-Seat Model)
    seat_count INTEGER NOT NULL DEFAULT 1,
    base_price_cents INTEGER NOT NULL DEFAULT 0, -- Base subscription cost
    per_seat_price_cents INTEGER NOT NULL DEFAULT 0, -- Cost per user seat
    total_amount_cents INTEGER NOT NULL DEFAULT 0, -- base_price + (seat_count * per_seat_price)
    currency VARCHAR(3) DEFAULT 'USD',
    billing_interval VARCHAR(20) DEFAULT 'monthly', -- 'monthly' | 'yearly'
    
    -- Billing Cycle
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    trial_ends_at TIMESTAMP WITH TIME ZONE,
    
    -- Cancellation
    cancel_at_period_end BOOLEAN DEFAULT false,
    canceled_at TIMESTAMP WITH TIME ZONE,
    
    -- Stripe Provider Info (for card mode)
    provider VARCHAR(50) NOT NULL DEFAULT 'stripe',
    provider_customer_id VARCHAR(255),
    provider_subscription_id VARCHAR(255) UNIQUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_tier CHECK (tier IN ('starter', 'professional', 'enterprise')),
    CONSTRAINT valid_payment_mode CHECK (payment_mode IN ('card', 'invoice')),
    CONSTRAINT valid_status CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete')),
    CONSTRAINT valid_interval CHECK (billing_interval IN ('monthly', 'yearly')),
    CONSTRAINT positive_seat_count CHECK (seat_count > 0)
);

CREATE INDEX idx_b2b_subscriptions_tenant ON b2b.subscriptions(tenant_id);
CREATE INDEX idx_b2b_subscriptions_tier ON b2b.subscriptions(tier);
CREATE INDEX idx_b2b_subscriptions_payment_mode ON b2b.subscriptions(payment_mode);
CREATE INDEX idx_b2b_subscriptions_status ON b2b.subscriptions(status);
CREATE INDEX idx_b2b_subscriptions_provider_id ON b2b.subscriptions(provider_subscription_id);

COMMENT ON TABLE b2b.subscriptions IS 'B2B tenant subscriptions with base + per-seat pricing model';
COMMENT ON COLUMN b2b.subscriptions.tier IS 'Subscription tier: starter, professional, enterprise';
COMMENT ON COLUMN b2b.subscriptions.payment_mode IS 'Payment method: card (Stripe) or invoice (wire transfer)';
COMMENT ON COLUMN b2b.subscriptions.seat_count IS 'Number of active user seats (calculated from active users)';
COMMENT ON COLUMN b2b.subscriptions.base_price_cents IS 'Base subscription cost in cents (tier-specific)';
COMMENT ON COLUMN b2b.subscriptions.per_seat_price_cents IS 'Cost per user seat in cents (tier-specific)';
COMMENT ON COLUMN b2b.subscriptions.total_amount_cents IS 'Total cost: base_price + (seat_count * per_seat_price)';

-- ============================================================================
-- INVOICES
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES b2b.subscriptions(id) ON DELETE SET NULL,
    tenant_id UUID REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    
    -- Invoice Identification
    invoice_number VARCHAR(50) UNIQUE NOT NULL, -- e.g., 'INV-2024-12-001'
    
    -- Provider Info (for card mode invoices from Stripe)
    provider VARCHAR(50) DEFAULT 'manual', -- 'stripe' | 'manual'
    provider_invoice_id VARCHAR(255) UNIQUE,
    
    -- Invoice Details
    status VARCHAR(50) DEFAULT 'draft',
    amount_due INTEGER NOT NULL, -- in cents
    amount_paid INTEGER DEFAULT 0, -- in cents
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Seat Snapshot (for audit trail)
    seat_count_snapshot INTEGER NOT NULL,
    base_price_snapshot_cents INTEGER NOT NULL,
    per_seat_price_snapshot_cents INTEGER NOT NULL,
    
    -- Billing Period
    billing_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    billing_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Dates
    invoice_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    due_date TIMESTAMP WITH TIME ZONE,
    paid_at TIMESTAMP WITH TIME ZONE,
    
    -- URLs (for Stripe invoices)
    invoice_pdf_url TEXT,
    hosted_invoice_url TEXT,
    
    -- Approval Workflow (for manual invoices)
    approved_by UUID, -- Platform admin user ID (no FK - platform schema may not exist yet)
    approved_at TIMESTAMP WITH TIME ZONE,
    
    -- Payment Confirmation (for manual invoices)
    marked_paid_by UUID, -- Platform admin user ID (no FK - platform schema may not exist yet)
    payment_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_invoice_status CHECK (status IN ('draft', 'pending_approval', 'approved', 'sent', 'paid', 'overdue', 'void'))
);

CREATE INDEX idx_b2b_invoices_subscription ON b2b.invoices(subscription_id);
CREATE INDEX idx_b2b_invoices_tenant ON b2b.invoices(tenant_id);
CREATE INDEX idx_b2b_invoices_number ON b2b.invoices(invoice_number);
CREATE INDEX idx_b2b_invoices_status ON b2b.invoices(status);
CREATE INDEX idx_b2b_invoices_due_date ON b2b.invoices(due_date);
CREATE INDEX idx_b2b_invoices_provider_id ON b2b.invoices(provider_invoice_id);

COMMENT ON TABLE b2b.invoices IS 'Monthly invoices for B2B subscriptions (both card and invoice payment modes)';
COMMENT ON COLUMN b2b.invoices.invoice_number IS 'Human-readable invoice identifier';
COMMENT ON COLUMN b2b.invoices.seat_count_snapshot IS 'Snapshot of seat count at invoice generation time';
COMMENT ON COLUMN b2b.invoices.status IS 'Invoice lifecycle: draft → pending_approval → approved → sent → paid/overdue';
COMMENT ON COLUMN b2b.invoices.approved_by IS 'Platform admin who approved the invoice';
COMMENT ON COLUMN b2b.invoices.marked_paid_by IS 'Platform admin who marked invoice as paid';

-- ============================================================================
-- SUBSCRIPTION EVENTS (Audit Trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.subscription_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES b2b.subscriptions(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    
    -- Event Details
    event_type VARCHAR(100) NOT NULL, -- e.g., 'subscription.created', 'subscription.upgraded', 'payment_mode.changed'
    provider VARCHAR(50) DEFAULT 'system', -- 'stripe' | 'system'
    provider_event_id VARCHAR(255),
    
    -- Event Data
    payload JSONB,
    
    -- Actor
    triggered_by UUID, -- User or admin who triggered the event
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_b2b_subscription_events_subscription ON b2b.subscription_events(subscription_id);
CREATE INDEX idx_b2b_subscription_events_tenant ON b2b.subscription_events(tenant_id);
CREATE INDEX idx_b2b_subscription_events_type ON b2b.subscription_events(event_type);
CREATE INDEX idx_b2b_subscription_events_created ON b2b.subscription_events(created_at DESC);

COMMENT ON TABLE b2b.subscription_events IS 'Audit trail for all subscription-related events';
COMMENT ON COLUMN b2b.subscription_events.event_type IS 'Event type (e.g., created, upgraded, payment_mode_changed)';
COMMENT ON COLUMN b2b.subscription_events.payload IS 'JSON payload with event details';

-- ============================================================================
-- PAYMENT MODE REQUESTS (Approval Workflow)
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.payment_mode_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES b2b.subscriptions(id) ON DELETE CASCADE,
    
    -- Request Details
    current_mode VARCHAR(20) NOT NULL, -- Current payment mode
    requested_mode VARCHAR(20) NOT NULL, -- Requested payment mode
    status VARCHAR(50) DEFAULT 'pending', -- 'pending' | 'approved' | 'rejected' | 'scheduled' | 'applied'
    
    -- Requester
    requested_by UUID REFERENCES b2b.users(id),
    request_reason TEXT,
    
    -- Reviewer
    reviewed_by UUID, -- Platform admin user ID (no FK - platform schema may not exist yet)
    reviewed_at TIMESTAMP WITH TIME ZONE,
    admin_notes TEXT,
    
    -- Scheduling (no mid-cycle changes)
    effective_date TIMESTAMP WITH TIME ZONE, -- When the change will take effect (next billing period start)
    applied_at TIMESTAMP WITH TIME ZONE, -- When the change was actually applied
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_payment_mode_request_status CHECK (status IN ('pending', 'approved', 'rejected', 'scheduled', 'applied')),
    CONSTRAINT different_modes CHECK (current_mode != requested_mode)
);

CREATE INDEX idx_b2b_payment_mode_requests_tenant ON b2b.payment_mode_requests(tenant_id);
CREATE INDEX idx_b2b_payment_mode_requests_subscription ON b2b.payment_mode_requests(subscription_id);
CREATE INDEX idx_b2b_payment_mode_requests_status ON b2b.payment_mode_requests(status);
CREATE INDEX idx_b2b_payment_mode_requests_effective_date ON b2b.payment_mode_requests(effective_date);

COMMENT ON TABLE b2b.payment_mode_requests IS 'Approval workflow for payment mode changes (card ↔ invoice)';
COMMENT ON COLUMN b2b.payment_mode_requests.status IS 'pending → approved/rejected → scheduled → applied';
COMMENT ON COLUMN b2b.payment_mode_requests.effective_date IS 'Change takes effect at next billing period boundary (no mid-cycle)';
COMMENT ON COLUMN b2b.payment_mode_requests.applied_at IS 'Actual timestamp when mode change was applied to subscription';

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on billing tables
ALTER TABLE b2b.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.subscription_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.payment_mode_requests ENABLE ROW LEVEL SECURITY;

-- Subscriptions: Tenant isolation + Platform admin access
DROP POLICY IF EXISTS subscriptions_tenant_isolation ON b2b.subscriptions;
CREATE POLICY subscriptions_tenant_isolation ON b2b.subscriptions
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

COMMENT ON POLICY subscriptions_tenant_isolation ON b2b.subscriptions IS 
    'Tenant isolation for subscriptions. Platform admins can access all.';

-- Invoices: Tenant isolation + Platform admin access
DROP POLICY IF EXISTS invoices_tenant_isolation ON b2b.invoices;
CREATE POLICY invoices_tenant_isolation ON b2b.invoices
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

COMMENT ON POLICY invoices_tenant_isolation ON b2b.invoices IS 
    'Tenant isolation for invoices. Platform admins can access all.';

-- Subscription Events: Read-only audit trail with tenant isolation
DROP POLICY IF EXISTS subscription_events_tenant_isolation ON b2b.subscription_events;
CREATE POLICY subscription_events_tenant_isolation ON b2b.subscription_events
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

COMMENT ON POLICY subscription_events_tenant_isolation ON b2b.subscription_events IS 
    'Tenant isolation for subscription events. Platform admins can access all.';

-- Payment Mode Requests: Tenant isolation + Platform admin access
DROP POLICY IF EXISTS payment_mode_requests_tenant_isolation ON b2b.payment_mode_requests;
CREATE POLICY payment_mode_requests_tenant_isolation ON b2b.payment_mode_requests
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

COMMENT ON POLICY payment_mode_requests_tenant_isolation ON b2b.payment_mode_requests IS 
    'Tenant isolation for payment mode requests. Platform admins can access all.';

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION b2b.update_billing_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON b2b.subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION b2b.update_billing_updated_at_column();

CREATE TRIGGER update_invoices_updated_at
    BEFORE UPDATE ON b2b.invoices
    FOR EACH ROW
    EXECUTE FUNCTION b2b.update_billing_updated_at_column();

CREATE TRIGGER update_payment_mode_requests_updated_at
    BEFORE UPDATE ON b2b.payment_mode_requests
    FOR EACH ROW
    EXECUTE FUNCTION b2b.update_billing_updated_at_column();

-- ============================================================================
-- SEED DATA: Default Starter Tier for Existing Tenants
-- ============================================================================

-- Create starter tier subscriptions for all existing active tenants without subscriptions
-- Pricing: Starter tier base = $0, per_seat = $10/month
INSERT INTO b2b.subscriptions (
    tenant_id,
    tier,
    payment_mode,
    status,
    seat_count,
    base_price_cents,
    per_seat_price_cents,
    total_amount_cents,
    billing_interval,
    current_period_start,
    current_period_end
)
SELECT 
    t.id,
    'starter',
    'card',
    'active',
    COALESCE((
        SELECT COUNT(*) 
        FROM b2b.users u 
        WHERE u.tenant_id = t.id 
        AND u.is_active = TRUE 
        AND u.deleted_at IS NULL
    ), 1), -- Default to 1 seat if no users yet
    0, -- Starter base price = $0
    1000, -- $10/seat in cents
    COALESCE((
        SELECT COUNT(*) * 1000
        FROM b2b.users u 
        WHERE u.tenant_id = t.id 
        AND u.is_active = TRUE 
        AND u.deleted_at IS NULL
    ), 1000), -- Total = seat_count * $10
    'monthly',
    NOW(),
    NOW() + INTERVAL '30 days'
FROM b2b.tenants t
WHERE t.is_active = TRUE
AND t.deleted_at IS NULL
AND NOT EXISTS (
    SELECT 1 FROM b2b.subscriptions s WHERE s.tenant_id = t.id
);
