-- ============================================================================
-- REGULATORY LIBRARY & SURVEILLANCE CONTROLS (Bank Surveillance)
-- ============================================================================

-- 1. REGULATORY DOCUMENTS
CREATE TABLE IF NOT EXISTS bank_surveillance.regulatory_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    
    title VARCHAR(255) NOT NULL,
    framework VARCHAR(100), -- e.g. MAS, SEC, FCA
    region_id UUID REFERENCES b2b.geographic_regions(id), -- Specific Region
    year INTEGER,
    version VARCHAR(20),
    storage_path TEXT, -- Path to PDF in object storage
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_regulatory_docs_tenant_id ON bank_surveillance.regulatory_documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_regulatory_docs_region ON bank_surveillance.regulatory_documents(region_id);

-- 2. SURVEILLANCE CONTROLS
CREATE TABLE IF NOT EXISTS bank_surveillance.surveillance_controls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    
    risk_typology VARCHAR(100) NOT NULL, -- e.g. Market Manipulation
    risk_indicator VARCHAR(100) NOT NULL, -- e.g. Load Shifting
    
    -- Link to Regulatory Library
    regulatory_id UUID REFERENCES bank_surveillance.regulatory_documents(id) ON DELETE SET NULL,
    regulatory_reference_text VARCHAR(255), -- Fallback or display name
    
    detection_methods JSONB DEFAULT '[]', -- e.g. ["Keyword", "Semantic"]
    status VARCHAR(50) DEFAULT 'Active', -- Active, Inactive, Draft
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_surveillance_controls_tenant_id ON bank_surveillance.surveillance_controls(tenant_id);
CREATE INDEX IF NOT EXISTS idx_surveillance_controls_regulatory ON bank_surveillance.surveillance_controls(regulatory_id);

-- RLS POLICIES

-- REGULATORY DOCUMENTS
ALTER TABLE bank_surveillance.regulatory_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_regulatory_documents ON bank_surveillance.regulatory_documents
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- SURVEILLANCE CONTROLS
ALTER TABLE bank_surveillance.surveillance_controls ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_surveillance_controls ON bank_surveillance.surveillance_controls
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
