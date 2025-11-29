-- Migration: Complete Platform System Separation
-- Purpose: Create a fully separate "platform" system parallel to the customer tenant system
-- Schema only - data seeding handled by scripts/seed_system_tenant.py

-- ============================================================================
-- STEP 1: Create platform_tenant table
-- ============================================================================

CREATE TABLE platform_tenant (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL DEFAULT 'SaaS Platform',
    firebase_tenant_id VARCHAR(255) UNIQUE NOT NULL,
    oidc_provider_id VARCHAR(255),
    
    -- Configuration
    email_domain VARCHAR(255),
    support_email VARCHAR(255),
    
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_platform_tenant_firebase_id ON platform_tenant(firebase_tenant_id);

-- Ensure singleton (only one platform tenant allowed)
CREATE UNIQUE INDEX idx_platform_tenant_singleton ON platform_tenant ((true));
COMMENT ON INDEX idx_platform_tenant_singleton IS 'Ensures only one platform tenant exists';

-- ============================================================================
-- STEP 2: Create platform_roles table
-- ============================================================================

CREATE TABLE platform_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_tenant_id UUID REFERENCES platform_tenant(id) ON DELETE CASCADE NOT NULL,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    
    is_system_role BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_platform_roles_name ON platform_roles(name);
CREATE INDEX idx_platform_roles_tenant ON platform_roles(platform_tenant_id);

-- ============================================================================
-- STEP 3: Create platform_users table
-- ============================================================================

CREATE TABLE platform_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_tenant_id UUID REFERENCES platform_tenant(id) ON DELETE CASCADE NOT NULL,
    platform_role_id UUID REFERENCES platform_roles(id) NOT NULL,
    
    email VARCHAR(255) UNIQUE NOT NULL,
    firebase_uid VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    
    is_active BOOLEAN DEFAULT true NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Email validation
    CONSTRAINT platform_users_email_check 
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

-- Indexes
CREATE INDEX idx_platform_users_email ON platform_users(email);
CREATE INDEX idx_platform_users_firebase_uid ON platform_users(firebase_uid);
CREATE INDEX idx_platform_users_role ON platform_users(platform_role_id);
CREATE INDEX idx_platform_users_tenant ON platform_users(platform_tenant_id);
CREATE INDEX idx_platform_users_active ON platform_users(is_active);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_platform_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER platform_users_updated_at
    BEFORE UPDATE ON platform_users
    FOR EACH ROW
    EXECUTE FUNCTION update_platform_users_updated_at();

-- ============================================================================
-- STEP 4: Create platform audit log
-- ============================================================================

CREATE TABLE platform_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_tenant_id UUID REFERENCES platform_tenant(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES platform_users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_platform_audit_user ON platform_audit_log(user_id);
CREATE INDEX idx_platform_audit_action ON platform_audit_log(action);
CREATE INDEX idx_platform_audit_resource ON platform_audit_log(resource_type, resource_id);
CREATE INDEX idx_platform_audit_created ON platform_audit_log(created_at DESC);
CREATE INDEX idx_platform_audit_tenant ON platform_audit_log(platform_tenant_id);

-- ============================================================================
-- STEP 5: Clean up customer system (remove platform references)
-- ============================================================================

-- Remove is_system_tenant column from customer tenants
ALTER TABLE tenants DROP COLUMN IF EXISTS is_system_tenant;

-- Note: Actual data cleanup (deleting old platform admin users/roles) 
-- will be handled by seed scripts

-- ============================================================================
-- Table Comments
-- ============================================================================

COMMENT ON TABLE platform_tenant IS 'The platform itself - singleton representing the SaaS platform';
COMMENT ON TABLE platform_users IS 'Platform users (admins, support, billing) - separate from customer users';
COMMENT ON TABLE platform_roles IS 'Platform-specific roles - separate from customer roles';
COMMENT ON TABLE platform_audit_log IS 'Audit trail for all platform user actions';
