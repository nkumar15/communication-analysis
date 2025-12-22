-- ============================================================================
-- B2B RBAC SCHEMA
-- ============================================================================
-- Roles, Resources, Actions, Role Templates
-- ============================================================================

-- 1. RESOURCES (Global/System-wide)
CREATE TABLE IF NOT EXISTS b2b.resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    description TEXT,
    is_system_resource BOOLEAN NOT NULL DEFAULT false,  -- True = tenant-level, False = team-level
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. ACTIONS (Global/System-wide)
CREATE TABLE IF NOT EXISTS b2b.actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 3. ROLES (Tenant-Specific)
CREATE TABLE IF NOT EXISTS b2b.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    CONSTRAINT unique_tenant_role UNIQUE(tenant_id, name)
);

CREATE INDEX IF NOT EXISTS idx_roles_tenant_id ON b2b.roles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_roles_name ON b2b.roles(name);

-- 4. ROLE PERMISSIONS (Link Role <-> Resource <-> Action)
CREATE TABLE IF NOT EXISTS b2b.role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES b2b.roles(id) ON DELETE CASCADE,
    resource_id UUID NOT NULL REFERENCES b2b.resources(id) ON DELETE CASCADE,
    action_id UUID NOT NULL REFERENCES b2b.actions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT unique_role_permission UNIQUE(role_id, resource_id, action_id)
);

CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON b2b.role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_resource_id ON b2b.role_permissions(resource_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_action_id ON b2b.role_permissions(action_id);

-- 5. ROLE TEMPLATES (For seeding new tenants)
CREATE TABLE IF NOT EXISTS b2b.role_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    permissions JSONB DEFAULT '[]'::jsonb NOT NULL, -- [{'resource': 'users', 'actions': ['read']}]
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_role_templates_is_default ON b2b.role_templates(is_default);

-- 6. TEAM ROLE DEFINITIONS (Team-level roles)
CREATE TABLE IF NOT EXISTS b2b.team_role_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '[]'::jsonb NOT NULL,
    is_system BOOLEAN DEFAULT FALSE NOT NULL,
    is_default BOOLEAN DEFAULT FALSE NOT NULL,
    sort_order INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT unique_tenant_team_role UNIQUE(tenant_id, name)
);

-- Note: user.role_id FK is added in 002 but referenced in 001. 
-- In 001, we added the column. Here we can ensure the FK exists or created in 001.
-- DANGER: 001 creates table users with role_id. 
-- My 001 script had: role_id UUID, -- FK to roles table (added in 002_rbac.sql)
-- So I should add the FK here.

ALTER TABLE b2b.users 
    ADD CONSTRAINT fk_users_role 
    FOREIGN KEY (role_id) REFERENCES b2b.roles(id);

ALTER TABLE b2b.team_members 
    ADD CONSTRAINT fk_team_members_team_role 
    FOREIGN KEY (team_role_id) REFERENCES b2b.team_role_definitions(id);

ALTER TABLE b2b.invitations 
    ADD CONSTRAINT fk_invitations_team_role 
    FOREIGN KEY (team_role_id) REFERENCES b2b.team_role_definitions(id);
