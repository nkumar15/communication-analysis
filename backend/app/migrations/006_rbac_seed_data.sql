-- Seed data for RBAC system
-- Run this after 005_rbac_system.sql

-- ============================================================================
-- SEED STANDARD ACTIONS
-- ============================================================================

INSERT INTO actions (name, display_name) VALUES
    ('read', 'View'),
    ('write', 'Create/Edit'),
    ('delete', 'Delete'),
    ('invite', 'Invite Users')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- SEED RESOURCES
-- ============================================================================

INSERT INTO resources (name, display_name, category, description) VALUES
    ('dashboard', 'Dashboard', 'Analytics', 'Statistics and overview'),
    ('users', 'User Management', 'Administration', 'Manage users and invitations'),
    ('roles', 'Role Management', 'Administration', 'Manage roles and permissions'),
    ('farmers', 'Farmer Management', 'Core', 'Farmer onboarding and data management')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- SEED DEFAULT ROLES FOR EACH TENANT
-- ============================================================================
-- This will be run per-tenant, so we use a function

CREATE OR REPLACE FUNCTION seed_tenant_roles(p_tenant_id INTEGER)
RETURNS VOID AS $$
DECLARE
    v_admin_role_id INTEGER;
    v_field_manager_role_id INTEGER;
    v_field_agent_role_id INTEGER;
    
    v_dashboard_id INTEGER;
    v_users_id INTEGER;
    v_roles_id INTEGER;
    v_farmers_id INTEGER;
    
    v_read_id INTEGER;
    v_write_id INTEGER;
    v_delete_id INTEGER;
    v_invite_id INTEGER;
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

-- Add comment
COMMENT ON FUNCTION seed_tenant_roles IS 'Seeds default roles and permissions for a tenant';
