-- ============================================================================
-- BANK SURVEILLANCE PLUGIN TABLES & BUSINESS DATA
-- ============================================================================
-- 1. Plugin Config Tables (Sensitivity, Regions)
-- 2. Business Tables (Investigations, Communications)
-- 3. Team Hierarchy View
-- ============================================================================

-- A. PLUGIN CONFIGURATION TABLES

-- Sensitivity Levels Table (Configuration Driven)
CREATE TABLE IF NOT EXISTS b2b.sensitivity_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL, -- e.g. TOP_SECRET
    level INTEGER NOT NULL,    -- e.g. 4
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name),
    UNIQUE(tenant_id, level)
);

CREATE INDEX IF NOT EXISTS idx_sensitivity_levels_tenant 
ON b2b.sensitivity_levels(tenant_id);

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

-- C. TEAM HIERARCHY

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
COMMENT ON TABLE b2b.sensitivity_levels IS 'Data classification levels (bank surveillance plugin)';
COMMENT ON MATERIALIZED VIEW b2b.team_hierarchy IS 'Hierarchical team structure (bank surveillance plugin)';

COMMENT ON COLUMN b2b.geographic_regions.code IS 'Region code (e.g., US, SG, MY)';
COMMENT ON COLUMN b2b.geographic_regions.regulatory_jurisdiction IS 'Primary regulator (e.g., SEC, MAS)';
COMMENT ON COLUMN b2b.geographic_regions.data_residency_rules IS 'JSON config for data residency compliance';


