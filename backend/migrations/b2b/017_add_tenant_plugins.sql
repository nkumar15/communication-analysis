-- Add plugins configuration column to tenants table
ALTER TABLE b2b.tenants ADD COLUMN IF NOT EXISTS plugins JSONB DEFAULT '[]'::jsonb;

-- Comment
COMMENT ON COLUMN b2b.tenants.plugins IS 'List of active plugins enabled for this tenant (e.g. ["geographic_boundaries"])';
