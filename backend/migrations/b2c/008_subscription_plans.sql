CREATE TABLE b2c.subscription_plans (
    tier TEXT PRIMARY KEY,
    limits JSONB NOT NULL DEFAULT '{}'::jsonb,
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trigger for updated_at
CREATE TRIGGER update_subscription_plans_updated_at
    BEFORE UPDATE ON b2c.subscription_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();
