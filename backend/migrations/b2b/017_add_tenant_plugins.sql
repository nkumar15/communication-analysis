-- Add features configuration column to tenants table
ALTER TABLE b2b.tenants ADD COLUMN IF NOT EXISTS features JSONB DEFAULT '{}'::jsonb;

-- Comment
COMMENT ON COLUMN b2b.tenants.features IS 'Full feature configuration for this tenant (e.g. {"sso": true, "plugins": ["geo"]})';
