-- ============================================================================
-- DOMAIN-SPECIFIC TABLE: FARMERS (Agriculture Placeholder)
-- ============================================================================
-- ⚠️ WARNING: This is NOT part of the SaaS boilerplate!
-- This is a domain-specific table for current development (agriculture).
-- In the future, this might be replaced with 'shops', 'products', etc.
--
-- Multi-tenant support with row-level ownership tracking.
-- The 'farmers' resource should be seeded via backend/scripts/b2b/seed_domain_data.py
-- ============================================================================

CREATE TABLE IF NOT EXISTS domain.farmers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    
    -- Farmer details
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    
    -- Row-level security (ownership tracking)
    created_by UUID NOT NULL REFERENCES b2b.users(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_farmers_tenant_id ON domain.farmers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_farmers_created_by ON domain.farmers(created_by);
CREATE INDEX IF NOT EXISTS idx_farmers_email ON domain.farmers(email);
CREATE INDEX IF NOT EXISTS idx_farmers_deleted_at ON domain.farmers(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE domain.farmers ENABLE ROW LEVEL SECURITY;

-- Policy: Farmers scoped to tenant
CREATE POLICY tenant_isolation_farmers ON domain.farmers
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

COMMENT ON POLICY tenant_isolation_farmers ON domain.farmers IS 
    'Enforces tenant isolation for farmers (domain-specific table)';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'domain' AND tablename = 'farmers' AND policyname = 'tenant_isolation_farmers';
    
    IF policy_count = 0 THEN
        RAISE EXCEPTION 'RLS policy not found for domain.farmers';
    END IF;
    
    RAISE NOTICE 'Farmers table RLS policy created successfully';
END $$;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE domain.farmers IS 'Farmer management with row-level security and multi-tenant support (domain-specific)';
COMMENT ON COLUMN domain.farmers.created_by IS 'User who created this farmer record (for row-level access control)';