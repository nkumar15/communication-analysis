-- ============================================================================
-- BUSINESS DATA TABLES (Bank Surveillance)
-- ============================================================================
-- 1. Investigations (Cases)
-- 2. Communications (Evidence)
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS bank_surveillance;

-- A. BUSINESS DATA TABLES

-- INVESTIGATIONS
CREATE TABLE IF NOT EXISTS bank_surveillance.investigations (
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
    sensitivity_level_id UUID REFERENCES b2b.sensitivity_levels(id),
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    closed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_investigations_tenant_id ON bank_surveillance.investigations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_investigations_team_id ON bank_surveillance.investigations(team_id);
CREATE INDEX IF NOT EXISTS idx_investigations_region ON bank_surveillance.investigations(data_region_id);
CREATE INDEX IF NOT EXISTS idx_investigations_sensitivity ON bank_surveillance.investigations(sensitivity_level_id);

-- COMMUNICATIONS
CREATE TABLE IF NOT EXISTS bank_surveillance.communications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES b2b.tenants(id) ON DELETE CASCADE NOT NULL,
    channel VARCHAR(50) NOT NULL, -- 'email', 'chat', 'voice'
    sub_channel VARCHAR(50), -- e.g. 'whatsapp', 'slack', 'gmail'
    message_id VARCHAR UNIQUE, -- Original Message-ID header or external ID
    sender VARCHAR(200) NOT NULL,
    recipients VARCHAR[], -- Array of recipient strings
    subject VARCHAR(200),
    content TEXT,
    flagged_keywords JSONB DEFAULT '[]',
    
    -- Metadata from plugins
    data_region_id UUID REFERENCES b2b.geographic_regions(id),
    sensitivity_level_id UUID REFERENCES b2b.sensitivity_levels(id),

    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_communications_tenant_id ON bank_surveillance.communications(tenant_id);

CREATE INDEX IF NOT EXISTS idx_communications_region ON bank_surveillance.communications(data_region_id);
CREATE INDEX IF NOT EXISTS idx_communications_sensitivity ON bank_surveillance.communications(sensitivity_level_id);


-- B. RLS POLICIES

-- INVESTIGATIONS
ALTER TABLE bank_surveillance.investigations ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_investigations ON bank_surveillance.investigations
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- COMMUNICATIONS
ALTER TABLE bank_surveillance.communications ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_communications ON bank_surveillance.communications
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
