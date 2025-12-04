
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

CREATE TABLE IF NOT EXISTS b2b.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL UNIQUE,
    firebase_tenant_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- Activation workflow fields
    activation_token VARCHAR(64) UNIQUE,
    activation_status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    activation_expires_at TIMESTAMP WITH TIME ZONE,
    activated_at TIMESTAMP WITH TIME ZONE,
    activated_by UUID,  -- FK constraint added later after users table exists
    activation_started_at TIMESTAMP WITH TIME ZONE,
    
    -- Status and timestamps
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
    
);

-- Indexes for tenants
CREATE INDEX IF NOT EXISTS idx_tenants_domain ON b2b.tenants(domain);
CREATE INDEX IF NOT EXISTS idx_tenants_firebase_id ON b2b.tenants(firebase_tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenants_activation_status ON b2b.tenants(activation_status);
CREATE INDEX IF NOT EXISTS idx_tenants_activation_token ON b2b.tenants(activation_token);
CREATE INDEX IF NOT EXISTS idx_tenants_activation_started ON b2b.tenants(activation_started_at);
CREATE INDEX IF NOT EXISTS idx_tenants_deleted_at ON b2b.tenants(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- USERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    firebase_uid VARCHAR(255) NOT NULL,
    
    -- Role fields (both legacy string and new RBAC reference)
    role VARCHAR(20) DEFAULT 'viewer',
    role_id UUID,  -- FK to roles table (added in 002_rbac.sql)
    
    -- Status and timestamps
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,    
    -- Unique constraints
    CONSTRAINT unique_tenant_email UNIQUE(tenant_id, email),
    CONSTRAINT unique_tenant_firebase_uid UNIQUE(tenant_id, firebase_uid)
);

-- Indexes for users
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON b2b.users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON b2b.users(email);
CREATE INDEX IF NOT EXISTS idx_users_firebase_uid ON b2b.users(firebase_uid);
CREATE INDEX IF NOT EXISTS idx_users_role ON b2b.users(role);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON b2b.users(role_id);
CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON b2b.users(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- INVITATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    
    -- Invitation token for acceptance link
    invitation_token VARCHAR(64) UNIQUE NOT NULL,
    
    -- Metadata
    invited_by UUID REFERENCES b2b.users(id),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    accepted_by UUID REFERENCES b2b.users(id),
    accepted_from_ip VARCHAR(45),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    -- Constraints
    CONSTRAINT unique_tenant_email_invitation UNIQUE(tenant_id, email)
);

-- Indexes for invitations
CREATE INDEX IF NOT EXISTS idx_invitations_tenant_id ON b2b.invitations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON b2b.invitations(invitation_token);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON b2b.invitations(email);
CREATE INDEX IF NOT EXISTS idx_invitations_expires_at ON b2b.invitations(expires_at);
CREATE INDEX IF NOT EXISTS idx_invitations_accepted_by ON b2b.invitations(accepted_by);
CREATE INDEX IF NOT EXISTS idx_invitations_deleted_at ON b2b.invitations(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_invitations_invited_by ON b2b.invitations(invited_by);

-- ============================================================================
-- TEAMS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    
    -- Team information
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Management
    created_by UUID REFERENCES b2b.users(id),
    
    -- Metadata
    config_data JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    -- Constraints
    CONSTRAINT unique_tenant_team_name UNIQUE(tenant_id, name)
);

-- Indexes for teams
CREATE INDEX IF NOT EXISTS idx_teams_tenant_id ON b2b.teams(tenant_id);
CREATE INDEX IF NOT EXISTS idx_teams_default ON b2b.teams(tenant_id, is_default) WHERE is_default = true;
CREATE INDEX IF NOT EXISTS idx_teams_created_by ON b2b.teams(created_by);
CREATE INDEX IF NOT EXISTS idx_teams_deleted_at ON b2b.teams(deleted_at) WHERE deleted_at IS NULL;

-- Ensure only one default team per tenant
CREATE UNIQUE INDEX IF NOT EXISTS idx_teams_one_default_per_tenant 
    ON b2b.teams(tenant_id) 
    WHERE is_default = true AND deleted_at IS NULL;

-- ============================================================================
-- TEAM MEMBERS TABLE (Many-to-Many)
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES b2b.teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES b2b.users(id) ON DELETE CASCADE,
    
    -- Team-specific role
    team_role VARCHAR(50) NOT NULL DEFAULT 'team_member',
    
    -- Timestamps
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT unique_team_user UNIQUE(team_id, user_id),
    CONSTRAINT valid_team_role CHECK (team_role IN ('team_manager', 'team_member', 'team_viewer'))
);

-- Indexes for team_members
CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON b2b.team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON b2b.team_members(user_id);
CREATE INDEX IF NOT EXISTS idx_team_members_role ON b2b.team_members(team_role);

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE b2b.tenants IS 'Multi-tenant organizations with Firebase GCIP integration';
COMMENT ON TABLE b2b.users IS 'User accounts with multi-tenant isolation and RBAC';
COMMENT ON TABLE b2b.invitations IS 'Pending user invitations with email-based workflow';
COMMENT ON TABLE b2b.teams IS 'Teams for organizing users within a B2B tenant';
COMMENT ON TABLE b2b.team_members IS 'Many-to-many relationship between teams and users';

COMMENT ON COLUMN b2b.tenants.activation_token IS 'Single-use token for tenant activation (48-hour expiry)';
COMMENT ON COLUMN b2b.tenants.activation_status IS 'Status: pending, active, expired';
COMMENT ON COLUMN b2b.tenants.firebase_tenant_id IS 'Firebase GCIP tenant identifier';

COMMENT ON COLUMN b2b.users.role IS 'Legacy role field: admin, field_manager, field_agent';
COMMENT ON COLUMN b2b.users.role_id IS 'RBAC role reference (replaces legacy role field)';

COMMENT ON COLUMN b2b.invitations.invitation_token IS 'Secure token for invitation acceptance link';
COMMENT ON COLUMN b2b.invitations.accepted_at IS 'Timestamp when invitation was accepted (NULL if pending)';

COMMENT ON COLUMN b2b.teams.is_default IS 'Default team where new users are assigned';
COMMENT ON COLUMN b2b.teams.config_data IS 'Additional team configuration in JSON format';
COMMENT ON COLUMN b2b.team_members.team_role IS 'User role within this specific team: team_manager, team_member, or team_viewer';

-- ============================================================================
-- ADDITIONAL COLUMNS FOR TEAMS FEATURE
-- ============================================================================

-- Add team_id to invitations (optional team assignment)
ALTER TABLE b2b.invitations ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES b2b.teams(id);
CREATE INDEX IF NOT EXISTS idx_invitations_team_id ON b2b.invitations(team_id);
COMMENT ON COLUMN b2b.invitations.team_id IS 'Team to assign user upon invitation acceptance (NULL = default team)';

-- Add team_role to invitations (team role for auto-assignment)
ALTER TABLE b2b.invitations ADD COLUMN IF NOT EXISTS team_role VARCHAR(50);
COMMENT ON COLUMN b2b.invitations.team_role IS 'Team role to assign if team_id is specified: team_manager, team_member, or team_viewer';


-- Add team_mode to tenants (single vs multiple teams configuration)
ALTER TABLE b2b.tenants ADD COLUMN team_mode VARCHAR(20) DEFAULT 'multiple' CHECK (team_mode IN ('single', 'multiple'));
COMMENT ON COLUMN b2b.tenants.team_mode IS 'Team configuration: single (one default team) or multiple (multi-team support)';

-- ============================================================================
-- FOREIGN KEY CONSTRAINTS (added after all tables exist)
-- ============================================================================

-- Add foreign key constraint for tenants.activated_by
ALTER TABLE b2b.tenants ADD CONSTRAINT fk_tenants_activated_by 
    FOREIGN KEY (activated_by) REFERENCES b2b.users(id);

-- ============================================================================
-- AUTH PROVIDERS TABLE (Multiple SSO providers per tenant)
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.auth_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    
    -- Provider type and identification
    provider_type VARCHAR(50) NOT NULL,  -- 'oidc', 'saml', 'google', 'microsoft', 'azure_ad'
    provider_id VARCHAR(255) NOT NULL,    -- Firebase provider ID (e.g., 'oidc.auth0', 'saml.okta')
    display_name VARCHAR(255),            -- Human-readable name (e.g., 'Auth0 SSO', 'Okta SAML')
    
    -- Configuration
    is_primary BOOLEAN DEFAULT false NOT NULL,   -- Primary provider for this tenant
    is_active BOOLEAN DEFAULT true NOT NULL,     -- Soft delete flag
    
    -- Metadata
    config_data JSONB,  -- Additional provider-specific configuration
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    -- Constraints
    CONSTRAINT unique_tenant_provider_id UNIQUE(tenant_id, provider_id),
    CONSTRAINT valid_provider_type CHECK (provider_type IN ('oidc', 'saml', 'google', 'microsoft', 'azure_ad'))
);

-- Indexes for auth_providers
CREATE INDEX IF NOT EXISTS idx_auth_providers_tenant_id ON b2b.auth_providers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_auth_providers_type ON b2b.auth_providers(provider_type);
CREATE INDEX IF NOT EXISTS idx_auth_providers_active ON b2b.auth_providers(is_active);
CREATE INDEX IF NOT EXISTS idx_auth_providers_primary ON b2b.auth_providers(tenant_id, is_primary) WHERE is_primary = true;
CREATE INDEX IF NOT EXISTS idx_auth_providers_deleted_at ON b2b.auth_providers(deleted_at) WHERE deleted_at IS NULL;

-- Create unique partial index to enforce single primary provider per tenant
CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_providers_one_primary_per_tenant 
    ON b2b.auth_providers(tenant_id) 
    WHERE is_primary = true AND is_active = true;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION b2b.update_auth_providers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auth_providers_updated_at
    BEFORE UPDATE ON b2b.auth_providers
    FOR EACH ROW
    EXECUTE FUNCTION b2b.update_auth_providers_updated_at();

-- Comments for auth_providers
COMMENT ON TABLE b2b.auth_providers IS 'Authentication providers configured for B2B tenants (OIDC, SAML, Google, Microsoft, etc.)';
COMMENT ON COLUMN b2b.auth_providers.provider_type IS 'Type of auth provider: oidc, saml, google, microsoft, azure_ad';
COMMENT ON COLUMN b2b.auth_providers.provider_id IS 'Firebase provider identifier (e.g., oidc.auth0, saml.okta)';
COMMENT ON COLUMN b2b.auth_providers.is_primary IS 'Primary authentication provider for this tenant';
COMMENT ON COLUMN b2b.auth_providers.config_data IS 'Additional provider-specific configuration in JSON format';
COMMENT ON INDEX b2b.idx_auth_providers_one_primary_per_tenant IS 'Ensures only one active primary provider per tenant';