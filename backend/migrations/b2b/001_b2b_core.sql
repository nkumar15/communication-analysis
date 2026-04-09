-- ============================================================================
-- B2B CORE SCHEMA
-- ============================================================================
-- Tenants, Users, Teams, Invitations (Core Structure)
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS b2b;

-- ============================================================================
-- 1. TENANTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL UNIQUE,
    firebase_tenant_id VARCHAR(255) NOT NULL UNIQUE,
    logo_url VARCHAR(500),
    domain_type VARCHAR(50) DEFAULT 'default',
    
    -- Activation workflow fields
    activation_token VARCHAR(64) UNIQUE,
    activation_status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    activation_expires_at TIMESTAMP WITH TIME ZONE,
    activated_at TIMESTAMP WITH TIME ZONE,
    activated_by UUID,  -- FK constraint added later after users table exists
    activation_started_at TIMESTAMP WITH TIME ZONE,
    
    -- Team Mode (single/multiple)
    team_mode VARCHAR(20) DEFAULT 'multiple' CHECK (team_mode IN ('single', 'multiple')),

    -- Status and timestamps
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_tenants_domain ON b2b.tenants(domain);
CREATE INDEX IF NOT EXISTS idx_tenants_firebase_id ON b2b.tenants(firebase_tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenants_activation_status ON b2b.tenants(activation_status);
CREATE INDEX IF NOT EXISTS idx_tenants_activation_token ON b2b.tenants(activation_token);
CREATE INDEX IF NOT EXISTS idx_tenants_deleted_at ON b2b.tenants(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- 2. USERS TABLE
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

CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON b2b.users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON b2b.users(email);
CREATE INDEX IF NOT EXISTS idx_users_firebase_uid ON b2b.users(firebase_uid);

-- ============================================================================
-- PLUGIN EXTENSIONS (Added for geographic_boundaries)
-- ============================================================================
ALTER TABLE b2b.users 
ADD COLUMN IF NOT EXISTS geographic_scopes UUID[] DEFAULT ARRAY[]::UUID[];

CREATE INDEX IF NOT EXISTS idx_users_geographic_scopes 
ON b2b.users USING GIN(geographic_scopes);


-- Now we can add the circular FK for tenants.activated_by
ALTER TABLE b2b.tenants ADD CONSTRAINT fk_tenants_activated_by 
    FOREIGN KEY (activated_by) REFERENCES b2b.users(id);

-- ============================================================================
-- 3. TEAMS & MEMBERS
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

CREATE INDEX IF NOT EXISTS idx_teams_tenant_id ON b2b.teams(tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_teams_one_default_per_tenant 
    ON b2b.teams(tenant_id) 
    WHERE is_default = true AND deleted_at IS NULL;

-- ============================================================================
-- PLUGIN EXTENSIONS (Added for hierarchical_teams)
-- ============================================================================
ALTER TABLE b2b.teams 
ADD COLUMN IF NOT EXISTS parent_team_id UUID REFERENCES b2b.teams(id);

ALTER TABLE b2b.teams 
ADD COLUMN IF NOT EXISTS team_type VARCHAR(50);

ALTER TABLE b2b.teams 
ADD COLUMN IF NOT EXISTS hierarchy_level INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_teams_parent ON b2b.teams(parent_team_id);
CREATE INDEX IF NOT EXISTS idx_teams_hierarchy ON b2b.teams(hierarchy_level);


-- Team Members
CREATE TABLE IF NOT EXISTS b2b.team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES b2b.teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES b2b.users(id) ON DELETE CASCADE,
    
    -- Team-specific role (legacy column)
    team_role VARCHAR(50) NOT NULL DEFAULT 'team_contributor',
    
    -- New team role FK (added in RBAC)
    team_role_id UUID, 
    
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT unique_team_user UNIQUE(team_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON b2b.team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON b2b.team_members(user_id);

-- ============================================================================
-- 4. INVITATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    
    -- Invitation token
    invitation_token VARCHAR(64) UNIQUE NOT NULL,
    
    -- Metadata
    invited_by UUID REFERENCES b2b.users(id),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    accepted_by UUID REFERENCES b2b.users(id),
    accepted_from_ip VARCHAR(45),
    
    -- Optional Team invite logic
    team_id UUID REFERENCES b2b.teams(id),
    team_role VARCHAR(50),
    team_role_id UUID, -- FK added in RBAC
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    CONSTRAINT unique_tenant_email_invitation UNIQUE(tenant_id, email)
);

CREATE INDEX IF NOT EXISTS idx_invitations_tenant_id ON b2b.invitations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON b2b.invitations(invitation_token);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON b2b.invitations(email);

-- ============================================================================
-- 5. AUTH PROVIDERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS b2b.auth_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    
    provider_type VARCHAR(50) NOT NULL,
    provider_id VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    
    is_primary BOOLEAN DEFAULT false NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    config_data JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    CONSTRAINT unique_tenant_provider_id UNIQUE(tenant_id, provider_id),
    CONSTRAINT valid_provider_type CHECK (provider_type IN ('oidc', 'saml', 'google', 'microsoft', 'azure_ad'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_providers_one_primary_per_tenant 
    ON b2b.auth_providers(tenant_id) 
    WHERE is_primary = true AND is_active = true;

-- Generic update trigger
CREATE OR REPLACE FUNCTION b2b.update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auth_providers_updated_at BEFORE UPDATE ON b2b.auth_providers FOR EACH ROW EXECUTE FUNCTION b2b.update_timestamp_column();
