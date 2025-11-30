-- Migration: Create auth_providers table for Platform
-- Purpose: Support multiple authentication provider types for platform admins
-- Schema: platform

-- ============================================================================
-- STEP 1: Create auth_providers table
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
    
    -- Constraints
    CONSTRAINT unique_platform_provider_id UNIQUE(platform_tenant_id, provider_id),
    CONSTRAINT valid_provider_type CHECK (provider_type IN ('oidc', 'saml', 'google', 'microsoft', 'azure_ad'))
);

-- ============================================================================
-- STEP 2: Create indexes
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_platform_auth_providers_tenant_id ON platform.auth_providers(platform_tenant_id);
CREATE INDEX IF NOT EXISTS idx_platform_auth_providers_type ON platform.auth_providers(provider_type);
CREATE INDEX IF NOT EXISTS idx_platform_auth_providers_active ON platform.auth_providers(is_active);
CREATE INDEX IF NOT EXISTS idx_platform_auth_providers_primary ON platform.auth_providers(platform_tenant_id, is_primary) WHERE is_primary = true;

-- ============================================================================
-- STEP 3: Create trigger for updated_at
-- ============================================================================

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

-- ============================================================================
-- STEP 4: Migrate existing oidc_provider_id data
-- ============================================================================

-- Migrate existing OIDC provider data from platform_tenant table
INSERT INTO platform.auth_providers (platform_tenant_id, provider_type, provider_id, display_name, is_primary, is_active)
SELECT 
    id AS platform_tenant_id,
    'oidc' AS provider_type,
    oidc_provider_id AS provider_id,
    'Platform SSO' AS display_name,
    true AS is_primary,
    true AS is_active
FROM platform.platform_tenant
WHERE oidc_provider_id IS NOT NULL
ON CONFLICT (platform_tenant_id, provider_id) DO NOTHING;

-- ============================================================================
-- STEP 5: Add comments for documentation
-- ============================================================================

COMMENT ON TABLE platform.auth_providers IS 'Authentication providers configured for platform administrators';
COMMENT ON COLUMN platform.auth_providers.provider_type IS 'Type of auth provider: oidc, saml, google, microsoft, azure_ad';
COMMENT ON COLUMN platform.auth_providers.provider_id IS 'Firebase provider identifier (e.g., oidc.auth0, saml.okta)';
COMMENT ON COLUMN platform.auth_providers.is_primary IS 'Primary authentication provider for platform';
COMMENT ON COLUMN platform.auth_providers.config_data IS 'Additional provider-specific configuration in JSON format';

-- ============================================================================
-- STEP 6: Add constraint to ensure only one primary provider
-- ============================================================================

-- Create unique partial index to enforce single primary provider
CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_auth_providers_one_primary 
    ON platform.auth_providers(platform_tenant_id) 
    WHERE is_primary = true AND is_active = true;

COMMENT ON INDEX platform.idx_platform_auth_providers_one_primary IS 'Ensures only one active primary provider for platform';
