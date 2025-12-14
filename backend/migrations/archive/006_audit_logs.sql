-- ============================================================================
-- AUDIT LOGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    actor_id UUID REFERENCES b2b.users(id) ON DELETE SET NULL,
    
    -- Event Details
    event_type VARCHAR(100) NOT NULL,  -- e.g., 'auth.login', 'user.created'
    resource_type VARCHAR(50) NOT NULL, -- e.g., 'user', 'team', 'project'
    resource_id UUID,                   -- ID of the resource being acted upon
    
    -- Metadata
    details JSONB DEFAULT '{}'::jsonb,  -- Flexible storage for changes/context
    ip_address VARCHAR(45),             -- IPv4 or IPv6
    user_agent TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes for audit_logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON b2b.audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_id ON b2b.audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON b2b.audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON b2b.audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON b2b.audit_logs(created_at DESC);

-- Comments
COMMENT ON TABLE b2b.audit_logs IS 'Immutable audit trail for security and compliance events';
COMMENT ON COLUMN b2b.audit_logs.actor_id IS 'User who performed the action (NULL for system events)';
COMMENT ON COLUMN b2b.audit_logs.details IS 'JSON payload containing event-specific metadata or state changes';


-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE b2b.audit_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Audit logs scoped to tenant
DROP POLICY IF EXISTS audit_logs_isolation_policy ON b2b.audit_logs;
CREATE POLICY audit_logs_isolation_policy ON b2b.audit_logs
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );  

COMMENT ON POLICY audit_logs_isolation_policy ON b2b.audit_logs IS 
    'Enforces tenant isolation for audit logs (domain-specific table)';
    