-- Simplified RBAC seed script for a single tenant
-- Insert standard actions
INSERT INTO b2b.actions (name, display_name) VALUES
    ('read', 'View'),
    ('write', 'Create/Edit'),
    ('delete', 'Delete'),
    ('invite', 'Invite Users')
ON CONFLICT (name) DO NOTHING;

-- Insert standard resources
INSERT INTO b2b.resources (name, display_name, category, description) VALUES
    ('dashboard', 'Dashboard', 'Analytics', 'Statistics and overview'),
    ('users', 'User Management', 'Administration', 'Manage users and invitations'),
    ('roles', 'Role Management', 'Administration', 'Manage roles and permissions'),
    ('farmers', 'Farmer Management', 'Core', 'Farmer onboarding and data management')
ON CONFLICT (name) DO NOTHING;

-- Insert ALL 3 roles in a single statement (admin, field_manager, field_agent)
INSERT INTO b2b.roles (tenant_id, name, display_name, description, is_system_role) VALUES
    ({tenant_id}, 'admin', 'Admin', 'System administrator with full access', TRUE),
    ({tenant_id}, 'field_manager', 'Field Manager', 'Manages field agents and oversees farmer onboarding', TRUE),
    ({tenant_id}, 'field_agent', 'Field Agent', 'Field executive responsible for farmer onboarding', TRUE)
ON CONFLICT (tenant_id, name) DO UPDATE SET display_name = EXCLUDED.display_name, description = EXCLUDED.description;

-- Admin permissions (all resources, all actions)
INSERT INTO b2b.role_permissions (role_id, resource_id, action_id)
SELECT r.id, res.id, act.id
FROM b2b.roles r
CROSS JOIN b2b.resources res
CROSS JOIN b2b.actions act
WHERE r.tenant_id = {tenant_id} AND r.name = 'admin'
ON CONFLICT (role_id, resource_id, action_id) DO NOTHING;

-- Field manager permissions (limited)
INSERT INTO b2b.role_permissions (role_id, resource_id, action_id)
SELECT r.id, res.id, act.id
FROM b2b.roles r
JOIN b2b.resources res ON res.name IN ('dashboard', 'users', 'roles', 'farmers')
JOIN b2b.actions act ON (
    (res.name = 'dashboard' AND act.name = 'read') OR
    (res.name = 'users' AND act.name IN ('read', 'invite')) OR
    (res.name = 'roles' AND act.name IN ('read', 'write')) OR
    (res.name = 'farmers' AND act.name IN ('read', 'write', 'delete'))
)
WHERE r.tenant_id = {tenant_id} AND r.name = 'field_manager'
ON CONFLICT (role_id, resource_id, action_id) DO NOTHING;

-- Field agent permissions (farmers only)
INSERT INTO b2b.role_permissions (role_id, resource_id, action_id)
SELECT r.id, res.id, act.id
FROM b2b.roles r
JOIN b2b.resources res ON res.name = 'farmers'
JOIN b2b.actions act ON act.name IN ('read', 'write')
WHERE r.tenant_id = {tenant_id} AND r.name = 'field_agent'
ON CONFLICT (role_id, resource_id, action_id) DO NOTHING;
