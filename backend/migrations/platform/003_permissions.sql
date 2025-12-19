-- Migration: Platform Permissions and Invitations
-- Purpose: Add granular RBAC permissions and user invitation system for platform

-- ============================================================================
-- STEP 1: Create platform_permissions table
-- ============================================================================

CREATE TABLE platform.platform_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_role_id UUID NOT NULL REFERENCES platform.platform_roles(id) ON DELETE CASCADE,
    
    resource VARCHAR(50) NOT NULL,  -- e.g. 'tenants', 'billing', 'users', 'invitations'
    action VARCHAR(50) NOT NULL,    -- e.g. 'read', 'write', 'delete', 'impersonate'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Ensure unique permission per role
    CONSTRAINT uq_role_resource_action UNIQUE (platform_role_id, resource, action)
);

-- Indexes
CREATE INDEX idx_platform_permissions_role ON platform.platform_permissions(platform_role_id);
CREATE INDEX idx_platform_permissions_resource ON platform.platform_permissions(resource);
CREATE INDEX idx_platform_permissions_action ON platform.platform_permissions(action);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION platform.update_platform_permissions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER platform_permissions_updated_at
    BEFORE UPDATE ON platform.platform_permissions
    FOR EACH ROW
    EXECUTE FUNCTION platform.update_platform_permissions_updated_at();

COMMENT ON TABLE platform.platform_permissions IS 'Granular permissions assigned to platform roles';
COMMENT ON COLUMN platform.platform_permissions.resource IS 'Resource type (e.g., tenants, billing, users)';
COMMENT ON COLUMN platform.platform_permissions.action IS 'Action on resource (e.g., read, write, delete)';

-- ============================================================================
-- STEP 2: Create invitation status enum type
-- ============================================================================

CREATE TYPE platform.invitation_status AS ENUM (
    'pending',
    'accepted',
    'expired',
    'revoked'
);

-- ============================================================================
-- STEP 3: Create platform_invitations table
-- ============================================================================

CREATE TABLE platform.platform_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_tenant_id UUID NOT NULL REFERENCES platform.platform_tenant(id) ON DELETE CASCADE,
    
    email VARCHAR(255) NOT NULL,
    platform_role_id UUID NOT NULL REFERENCES platform.platform_roles(id),
    
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    invited_by UUID NOT NULL REFERENCES platform.platform_users(id),
    status platform.invitation_status DEFAULT 'pending' NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes
CREATE INDEX idx_platform_invitations_email ON platform.platform_invitations(email);
CREATE INDEX idx_platform_invitations_token ON platform.platform_invitations(token);
CREATE INDEX idx_platform_invitations_status ON platform.platform_invitations(status);
CREATE INDEX idx_platform_invitations_tenant ON platform.platform_invitations(platform_tenant_id);
CREATE INDEX idx_platform_invitations_role ON platform.platform_invitations(platform_role_id);
CREATE INDEX idx_platform_invitations_invited_by ON platform.platform_invitations(invited_by);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION platform.update_platform_invitations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER platform_invitations_updated_at
    BEFORE UPDATE ON platform.platform_invitations
    FOR EACH ROW
    EXECUTE FUNCTION platform.update_platform_invitations_updated_at();

COMMENT ON TABLE platform.platform_invitations IS 'Invitations for new platform users (admins, support, etc.)';
COMMENT ON COLUMN platform.platform_invitations.token IS 'Unique token for invitation validation';
COMMENT ON COLUMN platform.platform_invitations.status IS 'Invitation status: pending, accepted, expired, or revoked';
