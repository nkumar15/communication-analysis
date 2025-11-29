-- Simplified RBAC seed script for a single tenant
-- Insert standard actions
INSERT INTO actions (name, display_name) VALUES
    ('read', 'View'),
    ('write', 'Create/Edit'),
    ('delete', 'Delete'),
    ('invite', 'Invite Users')
ON CONFLICT (name) DO NOTHING;

-- Insert standard resources
INSERT INTO resources (name, display_name, category, description) VALUES
    ('dashboard', 'Dashboard', 'Analytics', 'Statistics and overview'),
    ('users', 'User Management', 'Administration', 'Manage users and invitations'),
    ('roles', 'Role Management', 'Administration', 'Manage roles and permissions'),
    ('farmers', 'Farmer Management', 'Core', 'Farmer onboarding and data management')
ON CONFLICT (name) DO NOTHING;

-- Insert ALL 3 roles in a single statement (admin, field_manager, field_agent)
INSERT INTO roles (tenant_id, name, display_name, description, is_system_role) VALUES
    ({tenant_id}, 'admin', 'Admin', 'System administrator with full access', TRUE),
    ({tenant_id}, 'field_manager', 'Field Manager', 'Manages field agents and oversees farmer onboarding', TRUE),
    ({tenant_id}, 'field_agent', 'Field Agent', 'Field executive responsible for farmer onboarding', TRUE)
ON CONFLICT (tenant_id, name) DO UPDATE SET display_name = EXCLUDED.display_name, description = EXCLUDED.description;

-- Admin permissions (all resources, all actions)
INSERT INTO role_permissions (role_id, resource_id, action_id)
SELECT r.id, res.id, act.id
FROM roles r
CROSS JOIN resources res
CROSS JOIN actions act
WHERE r.tenant_id = {tenant_id} AND r.name = 'admin'
ON CONFLICT (role_id, resource_id, action_id) DO NOTHING;

-- Field manager permissions (limited)
INSERT INTO role_permissions (role_id, resource_id, action_id)
SELECT r.id, res.id, act.id
FROM roles r
JOIN resources res ON res.name IN ('dashboard', 'users', 'roles', 'farmers')
JOIN actions act ON (
    (res.name = 'dashboard' AND act.name = 'read') OR
    (res.name = 'users' AND act.name IN ('read', 'invite')) OR
    (res.name = 'roles' AND act.name IN ('read', 'write')) OR
    (res.name = 'farmers' AND act.name IN ('read', 'write', 'delete'))
)
WHERE r.tenant_id = {tenant_id} AND r.name = 'field_manager'
ON CONFLICT (role_id, resource_id, action_id) DO NOTHING;

-- Field agent permissions (farmers only)
INSERT INTO role_permissions (role_id, resource_id, action_id)
SELECT r.id, res.id, act.id
FROM roles r
JOIN resources res ON res.name = 'farmers'
JOIN actions act ON act.name IN ('read', 'write')
WHERE r.tenant_id = {tenant_id} AND r.name = 'field_agent'
ON CONFLICT (role_id, resource_id, action_id) DO NOTHING;
