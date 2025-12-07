-- Migration: Complete Platform System Separation
-- Purpose: Create a fully separate "platform" system parallel to the customer tenant system
-- Schema only - data seeding handled by scripts/seed_system_tenant.py

-- ============================================================================
-- STEP 1: Create platform_tenant table
-- ============================================================================

CREATE TABLE platform.platform_tenant (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL DEFAULT 'SaaS Platform',
    firebase_tenant_id VARCHAR(255) UNIQUE NOT NULL,
    oidc_provider_id VARCHAR(255),
    
    -- Configuration
    email_domain VARCHAR(255),
    support_email VARCHAR(255),
    
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_platform_tenant_firebase_id ON platform.platform_tenant(firebase_tenant_id);
CREATE INDEX IF NOT EXISTS idx_platform_tenant_deleted_at ON platform.platform_tenant(deleted_at) WHERE deleted_at IS NULL;

-- Ensure singleton (only one platform tenant allowed)
CREATE UNIQUE INDEX idx_platform_tenant_singleton ON platform.platform_tenant ((true));
COMMENT ON INDEX platform.idx_platform_tenant_singleton IS 'Ensures only one platform tenant exists';

-- ============================================================================
-- STEP 2: Create platform_roles table
-- ============================================================================

CREATE TABLE platform.platform_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_tenant_id UUID REFERENCES platform.platform_tenant(id) ON DELETE CASCADE NOT NULL,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    
    is_system_role BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP   ,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_platform_roles_name ON platform.platform_roles(name);
CREATE INDEX IF NOT EXISTS idx_platform_roles_tenant ON platform.platform_roles(platform_tenant_id);
CREATE INDEX IF NOT EXISTS idx_platform_roles_deleted_at ON platform.platform_roles(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- STEP 3: Create platform_users table
-- ============================================================================

CREATE TABLE platform.platform_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_tenant_id UUID REFERENCES platform.platform_tenant(id) ON DELETE CASCADE NOT NULL,
    platform_role_id UUID REFERENCES platform.platform_roles(id) NOT NULL,
    
    email VARCHAR(255) UNIQUE NOT NULL,
    firebase_uid VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    
    is_active BOOLEAN DEFAULT true NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    -- Email validation
    CONSTRAINT platform_users_email_check 
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

-- Indexes
CREATE INDEX idx_platform_users_email ON platform.platform_users(email);
CREATE INDEX idx_platform_users_firebase_uid ON platform.platform_users(firebase_uid);
CREATE INDEX idx_platform_users_role ON platform.platform_users(platform_role_id);
CREATE INDEX idx_platform_users_tenant ON platform.platform_users(platform_tenant_id);
CREATE INDEX idx_platform_users_active ON platform.platform_users(is_active);
CREATE INDEX IF NOT EXISTS idx_platform_users_deleted_at ON platform.platform_users(deleted_at) WHERE deleted_at IS NULL;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_platform_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER platform_users_updated_at
    BEFORE UPDATE ON platform.platform_users
    FOR EACH ROW
    EXECUTE FUNCTION update_platform_users_updated_at();

-- ============================================================================
-- STEP 4: Create platform audit log
-- ============================================================================

CREATE TABLE platform.platform_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_tenant_id UUID REFERENCES platform.platform_tenant(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES platform.platform_users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

-- Indexes
CREATE INDEX idx_platform_audit_user ON platform.platform_audit_log(user_id);   
CREATE INDEX idx_platform_audit_action ON platform.platform_audit_log(action);
CREATE INDEX idx_platform_audit_resource ON platform.platform_audit_log(resource_type, resource_id);
CREATE INDEX idx_platform_audit_created ON platform.platform_audit_log(created_at DESC);
CREATE INDEX idx_platform_audit_tenant ON platform.platform_audit_log(platform_tenant_id);
CREATE INDEX idx_platform_audit_deleted_at ON platform.platform_audit_log(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- STEP 5: Create auth_providers table for Platform SSO
-- ============================================================================

CREATE TABLE IF NOT EXISTS platform.auth_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_tenant_id UUID NOT NULL REFERENCES platform.platform_tenant(id) ON DELETE CASCADE,
    
    -- Provider type and identification
    provider_type VARCHAR(50) NOT NULL,  -- 'oidc', 'saml', 'google', 'microsoft', 'azure_ad'
    provider_id VARCHAR(255) NOT NULL,    -- Firebase provider ID (e.g., 'oidc.auth0', 'saml.okta')
    display_name VARCHAR(255),            -- Human-readable name (e.g., 'Platform OIDC', 'Google OAuth')
    
    -- Configuration
    is_primary BOOLEAN DEFAULT false NOT NULL,   -- Primary provider for platform
    is_active BOOLEAN DEFAULT true NOT NULL,     -- Soft delete flag
    
    -- Metadata
    config_data JSONB,  -- Additional provider-specific configuration
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    -- Constraints
    CONSTRAINT unique_platform_provider_id UNIQUE(platform_tenant_id, provider_id),
    CONSTRAINT valid_provider_type CHECK (provider_type IN ('oidc', 'saml', 'google', 'microsoft', 'azure_ad'))
);

-- Indexes for platform auth_providers
CREATE INDEX IF NOT EXISTS idx_platform_auth_providers_tenant_id ON platform.auth_providers(platform_tenant_id);
CREATE INDEX IF NOT EXISTS idx_platform_auth_providers_type ON platform.auth_providers(provider_type);
CREATE INDEX IF NOT EXISTS idx_platform_auth_providers_active ON platform.auth_providers(is_active);
CREATE INDEX IF NOT EXISTS idx_platform_auth_providers_primary ON platform.auth_providers(platform_tenant_id, is_primary) WHERE is_primary = true;
CREATE INDEX IF NOT EXISTS idx_platform_auth_providers_deleted_at ON platform.auth_providers(deleted_at) WHERE deleted_at IS NULL;

-- Create unique partial index to enforce single primary provider
CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_auth_providers_one_primary 
    ON platform.auth_providers(platform_tenant_id) 
    WHERE is_primary = true AND is_active = true;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION platform.update_auth_providers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auth_providers_updated_at
    BEFORE UPDATE ON platform.auth_providers
    FOR EACH ROW
    EXECUTE FUNCTION platform.update_auth_providers_updated_at();

-- Comments for platform auth_providers
COMMENT ON TABLE platform.auth_providers IS 'Authentication providers configured for platform administrators';
COMMENT ON COLUMN platform.auth_providers.provider_type IS 'Type of auth provider: oidc, saml, google, microsoft, azure_ad';
COMMENT ON COLUMN platform.auth_providers.provider_id IS 'Firebase provider identifier (e.g., oidc.auth0, saml.okta)';
COMMENT ON COLUMN platform.auth_providers.is_primary IS 'Primary authentication provider for platform';
COMMENT ON COLUMN platform.auth_providers.config_data IS 'Additional provider-specific configuration in JSON format';
COMMENT ON INDEX platform.idx_platform_auth_providers_one_primary IS 'Ensures only one active primary provider for platform';

-- ============================================================================
-- Table Comments
-- ============================================================================

COMMENT ON TABLE platform.platform_tenant IS 'The platform itself - singleton representing the SaaS platform';
COMMENT ON TABLE platform.platform_users IS 'Platform users (admins, support, billing) - separate from customer users';
COMMENT ON TABLE platform.platform_roles IS 'Platform-specific roles - separate from customer roles';
COMMENT ON TABLE platform.platform_audit_log IS 'Audit trail for all platform user actions';
