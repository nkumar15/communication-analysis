-- ============================================================================
-- FARMERS DOMAIN TABLE
-- ============================================================================
-- Farmers management with multi-tenant support and row-level ownership tracking
--
-- Key Changes:
--   - UUID primary keys
--   - Tenant isolation via tenant_id
--   - Ownership tracking via created_by
-- ============================================================================

CREATE TABLE IF NOT EXISTS farmers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Farmer details
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    
    -- Row-level security (ownership tracking)
    created_by UUID NOT NULL REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_farmers_tenant_id ON farmers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_farmers_created_by ON farmers(created_by);
CREATE INDEX IF NOT EXISTS idx_farmers_email ON farmers(email);

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE farmers IS 'Farmer management with row-level security and multi-tenant support';
COMMENT ON COLUMN farmers.created_by IS 'User who created this farmer record (for row-level access control)';
