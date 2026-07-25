-- ============================================================================
-- B2B AUDIT LOGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    actor_id UUID REFERENCES b2b.users(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON b2b.audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON b2b.audit_logs(created_at DESC);

-- RLS
ALTER TABLE b2b.audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_logs_isolation_policy ON b2b.audit_logs
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
