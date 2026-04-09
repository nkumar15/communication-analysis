-- ============================================================================
-- Risk Detection Workflow - Plugin Integration
-- ============================================================================
-- Creates risk detection tables and adds plugin columns
-- ============================================================================

-- ============================================================================
-- Table 1: Ingestion Config Templates (Global, shared across tenants)
-- ============================================================================

CREATE TABLE IF NOT EXISTS bank_surveillance.ingestion_config_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_default BOOLEAN DEFAULT false,
    
    -- Region Detection
    region_strategy VARCHAR(50) DEFAULT 'default',
    sender_domain_map JSONB DEFAULT '{}',
    
    -- Classification Detection
    classification_strategy VARCHAR(50) DEFAULT 'default',
    channel_map JSONB DEFAULT '{}',
    content_rules JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- Table 2: Ingestion Configs (Per-tenant, cloned from template)
-- ============================================================================

CREATE TABLE IF NOT EXISTS bank_surveillance.ingestion_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    template_id UUID REFERENCES bank_surveillance.ingestion_config_templates(id) ON DELETE SET NULL,
    
    -- Region Detection
    region_strategy VARCHAR(50) DEFAULT 'default',
    default_region_id UUID REFERENCES b2b.geographic_regions(id) ON DELETE SET NULL,
    fallback_region_id UUID REFERENCES b2b.geographic_regions(id) ON DELETE SET NULL,
    sender_domain_map JSONB DEFAULT '{}',
    
    -- Classification Detection
    classification_strategy VARCHAR(50) DEFAULT 'default',
    default_level_id UUID REFERENCES b2b.sensitivity_levels(id) ON DELETE SET NULL,
    channel_map JSONB DEFAULT '{}',
    content_rules JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    UNIQUE(tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_ingestion_configs_tenant_id 
    ON bank_surveillance.ingestion_configs(tenant_id);

-- ============================================================================
-- Add Missing Columns to Communications Table
-- ============================================================================

ALTER TABLE bank_surveillance.communications 
ADD COLUMN IF NOT EXISTS thread_id VARCHAR;

ALTER TABLE bank_surveillance.communications 
ADD COLUMN IF NOT EXISTS es_document_id VARCHAR UNIQUE;

ALTER TABLE bank_surveillance.communications 
ADD COLUMN IF NOT EXISTS analyzed BOOLEAN DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_communications_thread_id 
    ON bank_surveillance.communications(thread_id);

CREATE INDEX IF NOT EXISTS idx_communications_es_document_id 
    ON bank_surveillance.communications(es_document_id);

CREATE INDEX IF NOT EXISTS idx_communications_analyzed 
    ON bank_surveillance.communications(analyzed);

CREATE INDEX IF NOT EXISTS idx_communications_sender 
    ON bank_surveillance.communications(sender);
-- Table 3: Risk Events (Tier 1 - Individual detections)
-- ============================================================================

CREATE TABLE IF NOT EXISTS bank_surveillance.risk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    communication_id UUID NOT NULL REFERENCES bank_surveillance.communications(id) ON DELETE CASCADE,
    control_id UUID NOT NULL REFERENCES bank_surveillance.surveillance_controls(id) ON DELETE CASCADE,
    
    sender VARCHAR(200) NOT NULL,
    event_date DATE NOT NULL,
    match_type VARCHAR(50) NOT NULL,  -- keyword, regex, ml
    matched_keywords JSONB DEFAULT '[]',
    matched_snippet TEXT,
    match_score FLOAT DEFAULT 0.0,
    
    incident_id UUID,  -- Set during aggregation
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT uq_riskevent_comm_control UNIQUE(communication_id, control_id)
);

CREATE INDEX IF NOT EXISTS idx_risk_events_tenant_id ON bank_surveillance.risk_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_risk_events_sender ON bank_surveillance.risk_events(sender);
CREATE INDEX IF NOT EXISTS idx_risk_events_event_date ON bank_surveillance.risk_events(event_date);
CREATE INDEX IF NOT EXISTS idx_risk_events_incident_id ON bank_surveillance.risk_events(incident_id);

-- ============================================================================
-- Table 4: Incidents (Tier 2 - Aggregated signals)
-- ============================================================================

CREATE TABLE IF NOT EXISTS bank_surveillance.incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    control_id UUID NOT NULL REFERENCES bank_surveillance.surveillance_controls(id) ON DELETE CASCADE,
    
    sender VARCHAR(200) NOT NULL,
    incident_date DATE NOT NULL,
    event_count INTEGER DEFAULT 1,
    severity VARCHAR(20) DEFAULT 'low',
    status VARCHAR(20) DEFAULT 'open',
    
    alert_id UUID,  -- Set during alert generation
    
    -- Plugin Metadata
    data_region_ids UUID[] DEFAULT '{}',
    sensitivity_level_id UUID REFERENCES b2b.sensitivity_levels(id) ON DELETE SET NULL,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_incidents_tenant_id ON bank_surveillance.incidents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_incidents_sender ON bank_surveillance.incidents(sender);
CREATE INDEX IF NOT EXISTS idx_incidents_incident_date ON bank_surveillance.incidents(incident_date);
CREATE INDEX IF NOT EXISTS idx_incidents_alert_id ON bank_surveillance.incidents(alert_id);
CREATE INDEX IF NOT EXISTS idx_incidents_sensitivity_level ON bank_surveillance.incidents(sensitivity_level_id);
CREATE INDEX IF NOT EXISTS idx_incidents_data_region_ids ON bank_surveillance.incidents USING GIN(data_region_ids);

-- Add FK from risk_events to incidents (can only be added after incidents table exists)
ALTER TABLE bank_surveillance.risk_events 
ADD CONSTRAINT fk_risk_events_incident 
FOREIGN KEY (incident_id) REFERENCES bank_surveillance.incidents(id) ON DELETE SET NULL;

-- ============================================================================
-- Add applicable_regions to Surveillance Controls
-- ============================================================================

ALTER TABLE bank_surveillance.surveillance_controls 
ADD COLUMN IF NOT EXISTS applicable_regions UUID[] DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_surveillance_controls_applicable_regions 
    ON bank_surveillance.surveillance_controls USING GIN(applicable_regions);

-- ============================================================================
-- RLS Policies
-- ============================================================================

-- ingestion_configs
ALTER TABLE bank_surveillance.ingestion_configs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ingestion_configs_isolation_policy ON bank_surveillance.ingestion_configs;
CREATE POLICY ingestion_configs_isolation_policy ON bank_surveillance.ingestion_configs
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- risk_events
ALTER TABLE bank_surveillance.risk_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS risk_events_isolation_policy ON bank_surveillance.risk_events;
CREATE POLICY risk_events_isolation_policy ON bank_surveillance.risk_events
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- incidents
ALTER TABLE bank_surveillance.incidents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS incidents_isolation_policy ON bank_surveillance.incidents;
CREATE POLICY incidents_isolation_policy ON bank_surveillance.incidents
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- ============================================================================
-- Update Alerts Table (Schema Evolution)
-- ============================================================================

ALTER TABLE bank_surveillance.alerts 
ADD COLUMN IF NOT EXISTS subject VARCHAR(255);

ALTER TABLE bank_surveillance.alerts 
ALTER COLUMN communication_id DROP NOT NULL;

ALTER TABLE bank_surveillance.alerts 
ALTER COLUMN risk_type DROP NOT NULL;

CREATE INDEX IF NOT EXISTS idx_alerts_subject ON bank_surveillance.alerts(subject);

