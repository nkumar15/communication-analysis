-- ============================================================================
-- BUSINESS DATA TABLES (Bank Surveillance)
-- ============================================================================
-- 1. Investigations (Cases)
-- 2. Communications (Evidence)
-- ============================================================================

-- INVESTIGATIONS
CREATE TABLE IF NOT EXISTS b2b.investigations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    team_id UUID REFERENCES b2b.teams(id) ON DELETE SET NULL, -- Owning Desk (e.g. SG Team)
    assigned_to_user_id UUID REFERENCES b2b.users(id) ON DELETE SET NULL, -- Specific Analyst
    
    title VARCHAR(200) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    status VARCHAR(50) DEFAULT 'open',     -- open, investigating, closed, escalated
    
    -- PLUGIN COLUMNS
    data_region_id UUID REFERENCES b2b.geographic_regions(id),
    sensitivity b2b.sensitivity_level DEFAULT 'CONFIDENTIAL',
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    closed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_investigations_tenant_id ON b2b.investigations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_investigations_team_id ON b2b.investigations(team_id);
CREATE INDEX IF NOT EXISTS idx_investigations_region ON b2b.investigations(data_region_id);
CREATE INDEX IF NOT EXISTS idx_investigations_sensitivity ON b2b.investigations(sensitivity);

-- COMMUNICATIONS
CREATE TABLE IF NOT EXISTS b2b.communications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    investigation_id UUID REFERENCES b2b.investigations(id) ON DELETE SET NULL,
    
    channel VARCHAR(50) NOT NULL, -- email, chat, voice
    sender VARCHAR(200) NOT NULL,
    recipient VARCHAR(200) NOT NULL,
    subject VARCHAR(200),
    content TEXT,
    flagged_keywords JSONB, -- e.g. ["insider", "meeting"]
    
    -- PLUGIN COLUMNS
    data_region_id UUID REFERENCES b2b.geographic_regions(id),
    sensitivity b2b.sensitivity_level DEFAULT 'INTERNAL',
    
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_communications_tenant_id ON b2b.communications(tenant_id);
CREATE INDEX IF NOT EXISTS idx_communications_investigation ON b2b.communications(investigation_id);
CREATE INDEX IF NOT EXISTS idx_communications_region ON b2b.communications(data_region_id);

-- RLS POLICIES (Tenant Isolation)
ALTER TABLE b2b.investigations ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2b.communications ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_investigations ON b2b.investigations
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

CREATE POLICY tenant_isolation_communications ON b2b.communications
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
