-- ============================================================================
-- CORE SCHEMA: Tenants, Users, Invitations
-- ============================================================================
-- Consolidated migration combining:
--   - 001_initial.sql (tenants, users)
--   - 003_tenant_activation.sql (activation fields)
--   - 004_invitations_table.sql (invitations)
--
-- Key Changes:
--   - UUID primary keys (using gen_random_uuid(), PostgreSQL 13+)
--   - Multi-tenant isolation via tenant_id
--   - Activation workflow for tenant onboarding
--   - Invitation system for user management
-- ============================================================================

-- ============================================================================
-- TENANTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL UNIQUE,
    firebase_tenant_id VARCHAR(255) NOT NULL UNIQUE,
    oidc_provider_id VARCHAR(255),
    
    -- Activation workflow fields
    activation_token VARCHAR(64) UNIQUE,
    activation_status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    activation_expires_at TIMESTAMP WITH TIME ZONE,
    activated_at TIMESTAMP WITH TIME ZONE,
    activated_by UUID,  -- FK constraint added later after users table exists
    
    -- Status and timestamps
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes for tenants
CREATE INDEX IF NOT EXISTS idx_tenants_domain ON tenants(domain);
CREATE INDEX IF NOT EXISTS idx_tenants_firebase_id ON tenants(firebase_tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenants_activation_status ON tenants(activation_status);
CREATE INDEX IF NOT EXISTS idx_tenants_activation_token ON tenants(activation_token);

-- ============================================================================
-- USERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    firebase_uid VARCHAR(255) NOT NULL,
    
    -- Role fields (both legacy string and new RBAC reference)
    role VARCHAR(20) DEFAULT 'field_agent',
    role_id UUID,  -- FK to roles table (added in 002_rbac.sql)
    
    -- Hierarchy tracking
    invited_by UUID,  -- FK to users(id) - self-referential
    
    -- Status and timestamps
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Unique constraints
    CONSTRAINT unique_tenant_email UNIQUE(tenant_id, email),
    CONSTRAINT unique_tenant_firebase_uid UNIQUE(tenant_id, firebase_uid)
);

-- Indexes for users
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_firebase_uid ON users(firebase_uid);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_users_invited_by ON users(invited_by);

-- ============================================================================
-- INVITATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'field_agent',
    
    -- Invitation token for acceptance link
    invitation_token VARCHAR(64) UNIQUE NOT NULL,
    
    -- Metadata
    invited_by UUID REFERENCES users(id),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT unique_tenant_email_invitation UNIQUE(tenant_id, email)
);

-- Indexes for invitations
CREATE INDEX IF NOT EXISTS idx_invitations_tenant_id ON invitations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(invitation_token);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON invitations(email);
CREATE INDEX IF NOT EXISTS idx_invitations_expires_at ON invitations(expires_at);

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE tenants IS 'Multi-tenant organizations with Firebase GCIP integration';
COMMENT ON TABLE users IS 'User accounts with multi-tenant isolation and RBAC';
COMMENT ON TABLE invitations IS 'Pending user invitations with email-based workflow';

COMMENT ON COLUMN tenants.activation_token IS 'Single-use token for tenant activation (48-hour expiry)';
COMMENT ON COLUMN tenants.activation_status IS 'Status: pending, active, expired';
COMMENT ON COLUMN tenants.firebase_tenant_id IS 'Firebase GCIP tenant identifier';

COMMENT ON COLUMN users.role IS 'Legacy role field: admin, field_manager, field_agent';
COMMENT ON COLUMN users.role_id IS 'RBAC role reference (replaces legacy role field)';
COMMENT ON COLUMN users.invited_by IS 'User who invited this user (for hierarchy)';

COMMENT ON COLUMN invitations.invitation_token IS 'Secure token for invitation acceptance link';
COMMENT ON COLUMN invitations.accepted_at IS 'Timestamp when invitation was accepted (NULL if pending)';

-- ============================================================================
-- FOREIGN KEY CONSTRAINTS (added after all tables exist)
-- ============================================================================

-- Add foreign key constraint for tenants.activated_by
ALTER TABLE tenants ADD CONSTRAINT fk_tenants_activated_by 
    FOREIGN KEY (activated_by) REFERENCES users(id);
