-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TABLE b2c.subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier_key TEXT NOT NULL, -- logical identifier (e.g. 'premium')
    name TEXT NOT NULL,
    description TEXT,
    price_monthly INTEGER, -- in cents
    price_yearly INTEGER, -- in cents
    provider_config JSONB DEFAULT '{}'::jsonb, -- Store generic provider metadata
    limits JSONB NOT NULL DEFAULT '{}'::jsonb,
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Versioning & Lifecycle
    effective_from TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    archived_at TIMESTAMP WITH TIME ZONE,
    created_by UUID, -- Audit: Admin ID
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trigger for updated_at
CREATE TRIGGER update_subscription_plans_updated_at
    BEFORE UPDATE ON b2c.subscription_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- RLS Policies
ALTER TABLE b2c.subscription_plans ENABLE ROW LEVEL SECURITY;

-- Policy 1: Public Read (Active plans only)
-- Note: 'effective_from' check might need to be done in application logic if strictly needed, 
-- but RLS is safer. However, getting NOW() in RLS can be tricky with caching but usually fine in PG.
CREATE POLICY subscription_plans_select_public ON b2c.subscription_plans
    FOR SELECT
    USING (
        (effective_from <= NOW() AND archived_at IS NULL)
        OR 
        (current_setting('app.is_platform_admin', true) = 'true')
    );

-- Policy 2: Platform Admin Full Access
CREATE POLICY subscription_plans_all_admin ON b2c.subscription_plans
    FOR ALL
    USING (current_setting('app.is_platform_admin', true) = 'true')
    WITH CHECK (current_setting('app.is_platform_admin', true) = 'true');
