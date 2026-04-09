-- Create alerts table
CREATE TABLE IF NOT EXISTS bank_surveillance.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    communication_id UUID NOT NULL REFERENCES bank_surveillance.communications(id) ON DELETE CASCADE,
    risk_type VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'open',
    assigned_to UUID REFERENCES b2b.users(id) ON DELETE SET NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_alerts_tenant_id ON bank_surveillance.alerts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_alerts_communication_id ON bank_surveillance.alerts(communication_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON bank_surveillance.alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_assigned_to ON bank_surveillance.alerts(assigned_to);

-- RLS
ALTER TABLE bank_surveillance.alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_alerts ON bank_surveillance.alerts
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = (current_setting('app.current_tenant_id', true))::uuid
    );

-- Trigger for updated_at
CREATE TRIGGER update_bank_surveillance_alerts_modtime
    BEFORE UPDATE ON bank_surveillance.alerts
    FOR EACH ROW
    EXECUTE FUNCTION b2b.update_timestamp_column();
