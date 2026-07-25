-- Migration: 023_plugin_architecture_updates.sql
-- Purpose: Support master template catalog and tenant isolation for org tiers

-- 1. Create plugin_templates table
CREATE TABLE IF NOT EXISTS b2b.plugin_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_slug VARCHAR(50) NOT NULL UNIQUE,
    template_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plugin_templates_slug ON b2b.plugin_templates(plugin_slug);

-- 2. Update org_tiers for multi-tenancy
ALTER TABLE b2b.org_tiers 
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES b2b.tenants(id) ON DELETE CASCADE;

-- Remove global unique constraint on name (if exists)
ALTER TABLE b2b.org_tiers DROP CONSTRAINT IF EXISTS org_tiers_name_key;

-- Add composite unique constraint for tenant-based isolation
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ux_org_tier_tenant_name') THEN
        ALTER TABLE b2b.org_tiers 
        ADD CONSTRAINT ux_org_tier_tenant_name UNIQUE (tenant_id, name);
    END IF;
END $$;

-- 3. Enable RLS on org_tiers
ALTER TABLE b2b.org_tiers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS org_tier_isolation_policy ON b2b.org_tiers;
CREATE POLICY org_tier_isolation_policy ON b2b.org_tiers
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

CREATE INDEX IF NOT EXISTS idx_org_tiers_tenant_id ON b2b.org_tiers(tenant_id);

-- 4. Exclude plugin_templates from RLS (global catalog)
ALTER TABLE b2b.plugin_templates DISABLE ROW LEVEL SECURITY;
