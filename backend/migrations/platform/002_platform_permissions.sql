-- ============================================================================
-- PLATFORM PERMISSIONS & INVITES
-- ============================================================================

-- 1. PERMISSIONS
CREATE TABLE IF NOT EXISTS platform.platform_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_role_id UUID NOT NULL REFERENCES platform.platform_roles(id) ON DELETE CASCADE,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_role_resource_action UNIQUE (platform_role_id, resource, action)
);

CREATE OR REPLACE FUNCTION platform.update_platform_permissions_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER platform_permissions_updated_at BEFORE UPDATE ON platform.platform_permissions FOR EACH ROW EXECUTE FUNCTION platform.update_platform_permissions_updated_at();

-- 2. INVITATIONS
DO $$ BEGIN
    CREATE TYPE platform.invitation_status AS ENUM ('pending', 'accepted', 'expired', 'revoked');
EXCEPTION WHEN duplicate_object THEN null; END $$;

CREATE TABLE IF NOT EXISTS platform.platform_invitations (
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

CREATE OR REPLACE FUNCTION platform.update_platform_invitations_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER platform_invitations_updated_at BEFORE UPDATE ON platform.platform_invitations FOR EACH ROW EXECUTE FUNCTION platform.update_platform_invitations_updated_at();
