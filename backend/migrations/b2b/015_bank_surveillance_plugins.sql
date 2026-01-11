-- ============================================================================
-- BANK SURVEILLANCE PLUGIN TABLES
-- ============================================================================
-- Geographic Regions, Data Sensitivity, Hierarchical Teams
-- Requires: RBAC_PLUGINS env var to be set
-- ============================================================================

-- Sensitivity enum
DO $$ BEGIN
    CREATE TYPE b2b.sensitivity_level AS ENUM (
        'PUBLIC',
        'INTERNAL',
        'CONFIDENTIAL',
        'RESTRICTED',
        'TOP_SECRET'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Geographic Regions table
CREATE TABLE IF NOT EXISTS b2b.geographic_regions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    code VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    parent_region_id UUID REFERENCES b2b.geographic_regions(id),
    regulatory_jurisdiction VARCHAR(50),
    data_residency_rules JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, code)
);

CREATE INDEX IF NOT EXISTS idx_geographic_regions_tenant 
ON b2b.geographic_regions(tenant_id);

CREATE INDEX IF NOT EXISTS idx_geographic_regions_parent 
ON b2b.geographic_regions(parent_region_id);

-- Add data_region_id to surveillance resources
-- (Only if these tables exist - for bank surveillance use case)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'b2b' AND table_name = 'communications') THEN
        ALTER TABLE b2b.communications 
        ADD COLUMN IF NOT EXISTS data_region_id UUID REFERENCES b2b.geographic_regions(id);
        
        ALTER TABLE b2b.communications 
        ADD COLUMN IF NOT EXISTS sensitivity b2b.sensitivity_level DEFAULT 'INTERNAL';
        
        CREATE INDEX IF NOT EXISTS idx_communications_region 
        ON b2b.communications(data_region_id);
        
        CREATE INDEX IF NOT EXISTS idx_communications_sensitivity 
        ON b2b.communications(sensitivity);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'b2b' AND table_name = 'investigations') THEN
        ALTER TABLE b2b.investigations 
        ADD COLUMN IF NOT EXISTS data_region_id UUID REFERENCES b2b.geographic_regions(id);
        
        ALTER TABLE b2b.investigations 
        ADD COLUMN IF NOT EXISTS sensitivity b2b.sensitivity_level DEFAULT 'CONFIDENTIAL';
        
        CREATE INDEX IF NOT EXISTS idx_investigations_region 
        ON b2b.investigations(data_region_id);
        
        CREATE INDEX IF NOT EXISTS idx_investigations_sensitivity 
        ON b2b.investigations(sensitivity);
    END IF;
END $$;

-- Team hierarchy materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS b2b.team_hierarchy AS
WITH RECURSIVE team_tree AS (
    SELECT 
        id,
        parent_team_id,
        tenant_id,
        name,
        team_type,
        hierarchy_level,
        ARRAY[id] as path,
        id as root_team_id
    FROM b2b.teams
    WHERE parent_team_id IS NULL
    
    UNION ALL
    
    SELECT
        t.id,
        t.parent_team_id,
        t.tenant_id,
        t.name,
        t.team_type,
        t.hierarchy_level,
        tt.path || t.id,
        tt.root_team_id
    FROM b2b.teams t
    JOIN team_tree tt ON t.parent_team_id = tt.id
)
SELECT * FROM team_tree;

CREATE UNIQUE INDEX IF NOT EXISTS idx_team_hierarchy_id 
ON b2b.team_hierarchy(id);

-- ============================================================================
-- RLS POLICIES (Multi-Tenancy Isolation)
-- ============================================================================

-- GEOGRAPHIC REGIONS
ALTER TABLE b2b.geographic_regions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS geographic_region_isolation_policy ON b2b.geographic_regions;
CREATE POLICY geographic_region_isolation_policy ON b2b.geographic_regions
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE b2b.geographic_regions IS 'Regional boundaries for data access control (bank surveillance plugin)';
COMMENT ON TYPE b2b.sensitivity_level IS 'Data classification levels (bank surveillance plugin)';
COMMENT ON MATERIALIZED VIEW b2b.team_hierarchy IS 'Hierarchical team structure (bank surveillance plugin)';

COMMENT ON COLUMN b2b.geographic_regions.code IS 'Region code (e.g., AMER, EMEA, APAC)';
COMMENT ON COLUMN b2b.geographic_regions.regulatory_jurisdiction IS 'Primary regulator (e.g., SEC, FCA, MAS)';
COMMENT ON COLUMN b2b.geographic_regions.data_residency_rules IS 'JSON config for data residency compliance';

-- Note: RLS on communications/investigations tables handled by their respective migration files
