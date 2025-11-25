-- ============================================================================
-- RBAC SYSTEM: Roles, Resources, Actions, Permissions
-- ============================================================================
-- Consolidated migration combining:
--   - 005_rbac_system.sql (RBAC tables)
--   - 006_rbac_seed_data.sql (seed data and functions)
--
-- Key Changes:
--   - UUID primary keys throughout
--   - Tenant-scoped roles
--   - Application-wide resources and actions
--   - Seed data for default roles and permissions
-- ============================================================================

-- ============================================================================
-- RBAC CORE TABLES
-- ============================================================================

-- Roles table (tenant-scoped)
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,                  -- Internal name: 'admin', 'field_manager'
    display_name VARCHAR(100) NOT NULL,         -- UI name: 'Admin', 'Field Manager'
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,       -- Cannot be deleted
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT unique_tenant_role_name UNIQUE(tenant_id, name)
);

-- Resources table (application-wide, reusable across tenants)
CREATE TABLE IF NOT EXISTS resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,           -- 'dashboard', 'users', 'farmers'
    display_name VARCHAR(100) NOT NULL,         -- 'Dashboard', 'User Management'
    category VARCHAR(50),                        -- Group in UI: 'Administration', 'Core'
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT unique_resource_name UNIQUE(name)
);

-- Actions table (generic, reusable)
CREATE TABLE IF NOT EXISTS actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,                  -- 'read', 'write', 'delete', 'invite'
    display_name VARCHAR(100) NOT NULL,         -- 'View', 'Create/Edit', 'Delete'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT unique_action_name UNIQUE(name)
);

-- Role Permissions (maps roles to resource+action combinations)
CREATE TABLE IF NOT EXISTS role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT unique_role_resource_action UNIQUE(role_id, resource_id, action_id)
);

-- ============================================================================
-- UPDATE USERS TABLE WITH RBAC FOREIGN KEYS
-- ============================================================================

-- Add foreign key constraint to users.role_id (column already exists from 001_schema.sql)
ALTER TABLE users ADD CONSTRAINT fk_users_role_id 
    FOREIGN KEY (role_id) REFERENCES roles(id);

-- Add foreign key constraint to users.invited_by (self-referential)
ALTER TABLE users ADD CONSTRAINT fk_users_invited_by 
    FOREIGN KEY (invited_by) REFERENCES users(id);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_roles_tenant_id ON roles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_resource_id ON role_permissions(resource_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_action_id ON role_permissions(action_id);

-- ============================================================================
-- SEED DATA: ACTIONS
-- ============================================================================

INSERT INTO actions (name, display_name) VALUES
    ('read', 'View'),
    ('write', 'Create/Edit'),
    ('delete', 'Delete'),
    ('invite', 'Invite Users')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- SEED DATA: RESOURCES
-- ============================================================================

INSERT INTO resources (name, display_name, category, description) VALUES
    ('dashboard', 'Dashboard', 'Analytics', 'Statistics and overview'),
    ('users', 'User Management', 'Administration', 'Manage users and invitations'),
    ('roles', 'Role Management', 'Administration', 'Manage roles and permissions'),
    ('farmers', 'Farmer Management', 'Core', 'Farmer onboarding and data management')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- FUNCTION: SEED TENANT ROLES
-- ============================================================================

CREATE OR REPLACE FUNCTION seed_tenant_roles(p_tenant_id UUID)
RETURNS VOID AS $$
DECLARE
    v_admin_role_id UUID;
    v_field_manager_role_id UUID;
    v_field_agent_role_id UUID;
    
    v_dashboard_id UUID;
    v_users_id UUID;
    v_roles_id UUID;
    v_farmers_id UUID;
    
    v_read_id UUID;
    v_write_id UUID;
    v_delete_id UUID;
    v_invite_id UUID;
BEGIN
    -- Get resource IDs
    SELECT id INTO v_dashboard_id FROM resources WHERE name = 'dashboard';
    SELECT id INTO v_users_id FROM resources WHERE name = 'users';
    SELECT id INTO v_roles_id FROM resources WHERE name = 'roles';
    SELECT id INTO v_farmers_id FROM resources WHERE name = 'farmers';
    
    -- Get action IDs
    SELECT id INTO v_read_id FROM actions WHERE name = 'read';
    SELECT id INTO v_write_id FROM actions WHERE name = 'write';
    SELECT id INTO v_delete_id FROM actions WHERE name = 'delete';
    SELECT id INTO v_invite_id FROM actions WHERE name = 'invite';
    
    -- ========================================================================
    -- ADMIN ROLE - Full access to everything
    -- ========================================================================
    INSERT INTO roles (tenant_id, name, display_name, description, is_system_role)
    VALUES (p_tenant_id, 'admin', 'Admin', 'System administrator with full access', TRUE)
    ON CONFLICT (tenant_id, name) DO UPDATE 
    SET display_name = EXCLUDED.display_name,
        description = EXCLUDED.description
    RETURNING id INTO v_admin_role_id;
    
    -- Admin permissions: ALL
    INSERT INTO role_permissions (role_id, resource_id, action_id) VALUES
        -- Dashboard
        (v_admin_role_id, v_dashboard_id, v_read_id),
        -- Users
        (v_admin_role_id, v_users_id, v_read_id),
        (v_admin_role_id, v_users_id, v_write_id),
        (v_admin_role_id, v_users_id, v_delete_id),
        (v_admin_role_id, v_users_id, v_invite_id),
        -- Roles
        (v_admin_role_id, v_roles_id, v_read_id),
        (v_admin_role_id, v_roles_id, v_write_id),
        -- Farmers
        (v_admin_role_id, v_farmers_id, v_read_id),
        (v_admin_role_id, v_farmers_id, v_write_id),
        (v_admin_role_id, v_farmers_id, v_delete_id)
    ON CONFLICT (role_id, resource_id, action_id) DO NOTHING;
    
    -- ========================================================================
    -- FIELD MANAGER ROLE - Manage team and view dashboard
    -- ========================================================================
    INSERT INTO roles (tenant_id, name, display_name, description, is_system_role)
    VALUES (p_tenant_id, 'field_manager', 'Field Manager', 'Manages field agents and oversees farmer onboarding', TRUE)
    ON CONFLICT (tenant_id, name) DO UPDATE 
    SET display_name = EXCLUDED.display_name,
        description = EXCLUDED.description
    RETURNING id INTO v_field_manager_role_id;
    
    -- Field Manager permissions
    INSERT INTO role_permissions (role_id, resource_id, action_id) VALUES
        -- Dashboard (read only)
        (v_field_manager_role_id, v_dashboard_id, v_read_id),
        -- Users (read + invite agents only)
        (v_field_manager_role_id, v_users_id, v_read_id),
        (v_field_manager_role_id, v_users_id, v_invite_id),
        -- Roles (read + write for managing permissions)
        (v_field_manager_role_id, v_roles_id, v_read_id),
        (v_field_manager_role_id, v_roles_id, v_write_id),
        -- Farmers (full access to team's farmers)
        (v_field_manager_role_id, v_farmers_id, v_read_id),
        (v_field_manager_role_id, v_farmers_id, v_write_id),
        (v_field_manager_role_id, v_farmers_id, v_delete_id)
    ON CONFLICT (role_id, resource_id, action_id) DO NOTHING;
    
    -- ========================================================================
    -- FIELD AGENT ROLE - Only farmer data entry
    -- ========================================================================
    INSERT INTO roles (tenant_id, name, display_name, description, is_system_role)
    VALUES (p_tenant_id, 'field_agent', 'Field Agent', 'Field executive responsible for farmer onboarding', TRUE)
    ON CONFLICT (tenant_id, name) DO UPDATE 
    SET display_name = EXCLUDED.display_name,
        description = EXCLUDED.description
    RETURNING id INTO v_field_agent_role_id;
    
    -- Field Agent permissions (farmers only)
    INSERT INTO role_permissions (role_id, resource_id, action_id) VALUES
        (v_field_agent_role_id, v_farmers_id, v_read_id),
        (v_field_agent_role_id, v_farmers_id, v_write_id)
    ON CONFLICT (role_id, resource_id, action_id) DO NOTHING;
    
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SEED ROLES FOR EXISTING TENANTS
-- ============================================================================

-- Seed roles for all existing tenants
DO $$
DECLARE
    tenant_record RECORD;
BEGIN
    FOR tenant_record IN SELECT id FROM tenants
    LOOP
        PERFORM seed_tenant_roles(tenant_record.id);
    END LOOP;
END $$;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE roles IS 'Tenant-specific roles with customizable permissions';
COMMENT ON TABLE resources IS 'Application resources (features/modules) that can be controlled';
COMMENT ON TABLE actions IS 'Generic actions that can be performed on resources';
COMMENT ON TABLE role_permissions IS 'Maps roles to allowed resource+action combinations';

COMMENT ON COLUMN roles.name IS 'Internal role identifier (lowercase, no spaces)';
COMMENT ON COLUMN roles.display_name IS 'Human-readable role name shown in UI';
COMMENT ON COLUMN roles.is_system_role IS 'System roles cannot be deleted (admin, field_manager, field_agent)';

COMMENT ON FUNCTION seed_tenant_roles IS 'Seeds default roles and permissions for a tenant';
