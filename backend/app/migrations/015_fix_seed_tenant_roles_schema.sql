-- ============================================================================
-- Fix seed_tenant_roles function to use b2b schema
-- ============================================================================
-- This migration updates the seed_tenant_roles function to correctly reference
-- tables in the b2b schema after Phase 2 schema reorganization

DROP FUNCTION IF EXISTS seed_tenant_roles(UUID);

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
    -- Get resource IDs (from b2b schema)
    SELECT id INTO v_dashboard_id FROM b2b.resources WHERE name = 'dashboard';
    SELECT id INTO v_users_id FROM b2b.resources WHERE name = 'users';
    SELECT id INTO v_roles_id FROM b2b.resources WHERE name = 'roles';
    SELECT id INTO v_farmers_id FROM b2b.resources WHERE name = 'farmers';
    
    -- Get action IDs (from b2b schema)
    SELECT id INTO v_read_id FROM b2b.actions WHERE name = 'read';
    SELECT id INTO v_write_id FROM b2b.actions WHERE name = 'write';
    SELECT id INTO v_delete_id FROM b2b.actions WHERE name = 'delete';
    SELECT id INTO v_invite_id FROM b2b.actions WHERE name = 'invite';
    
    -- ========================================================================
    -- ADMIN ROLE - Full access to everything
    -- ========================================================================
    INSERT INTO b2b.roles (tenant_id, name, display_name, description, is_system_role)
    VALUES (p_tenant_id, 'admin', 'Admin', 'System administrator with full access', TRUE)
    ON CONFLICT (tenant_id, name) DO UPDATE 
    SET display_name = EXCLUDED.display_name,
        description = EXCLUDED.description
    RETURNING id INTO v_admin_role_id;
    
    -- Admin permissions: ALL
    INSERT INTO b2b.role_permissions (role_id, resource_id, action_id) VALUES
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
    INSERT INTO b2b.roles (tenant_id, name, display_name, description, is_system_role)
    VALUES (p_tenant_id, 'field_manager', 'Field Manager', 'Manages field agents and oversees farmer onboarding', TRUE)
    ON CONFLICT (tenant_id, name) DO UPDATE 
    SET display_name = EXCLUDED.display_name,
        description = EXCLUDED.description
    RETURNING id INTO v_field_manager_role_id;
    
    -- Field Manager permissions
    INSERT INTO b2b.role_permissions (role_id, resource_id, action_id) VALUES
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
    INSERT INTO b2b.roles (tenant_id, name, display_name, description, is_system_role)
    VALUES (p_tenant_id, 'field_agent', 'Field Agent', 'Field executive responsible for farmer onboarding', TRUE)
    ON CONFLICT (tenant_id, name) DO UPDATE 
    SET display_name = EXCLUDED.display_name,
        description = EXCLUDED.description
    RETURNING id INTO v_field_agent_role_id;
    
    -- Field Agent permissions (farmers only)
    INSERT INTO b2b.role_permissions (role_id, resource_id, action_id) VALUES
        (v_field_agent_role_id, v_farmers_id, v_read_id),
        (v_field_agent_role_id, v_farmers_id, v_write_id)
    ON CONFLICT (role_id, resource_id, action_id) DO NOTHING;
    
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION seed_tenant_roles IS 'Seeds default roles and permissions for a tenant (updated for b2b schema)';
