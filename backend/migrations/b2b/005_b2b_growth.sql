-- ============================================================================
-- B2B GROWTH SCHEMA
-- ============================================================================
-- Bulk Invitations and potential viral features
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.bulk_invite_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES b2b.users(id) ON DELETE SET NULL,
    total_rows INT NOT NULL CHECK (total_rows > 0),
    successful_count INT NOT NULL DEFAULT 0 CHECK (successful_count >= 0),
    failed_count INT NOT NULL DEFAULT 0 CHECK (failed_count >= 0),
    results JSONB NOT NULL DEFAULT '{"rows": []}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT bulk_invite_jobs_counts_valid 
        CHECK (successful_count + failed_count = total_rows)
);

CREATE INDEX idx_bulk_invite_jobs_tenant_created ON b2b.bulk_invite_jobs(tenant_id, created_at DESC);

-- RLS
ALTER TABLE b2b.bulk_invite_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY bulk_invite_jobs_tenant_isolation ON b2b.bulk_invite_jobs
    USING (tenant_id::text = current_setting('app.current_tenant_id', TRUE));
