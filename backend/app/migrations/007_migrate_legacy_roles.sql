-- Migration: Migrate legacy roles to RBAC system

-- 1. Update users.role_id based on legacy role column
-- Admin -> admin
UPDATE users
SET role_id = (
    SELECT id FROM roles 
    WHERE name = 'admin' 
    AND roles.tenant_id = users.tenant_id
)
WHERE role = 'admin';

-- Manager -> field_manager
UPDATE users
SET role_id = (
    SELECT id FROM roles 
    WHERE name = 'field_manager' 
    AND roles.tenant_id = users.tenant_id
)
WHERE role = 'manager';

-- Member/Field Agent -> field_agent
UPDATE users
SET role_id = (
    SELECT id FROM roles 
    WHERE name = 'field_agent' 
    AND roles.tenant_id = users.tenant_id
)
WHERE role IN ('member', 'field_agent');

-- 2. Update invitations to use new role names
UPDATE invitations SET role = 'field_manager' WHERE role = 'manager';
UPDATE invitations SET role = 'field_agent' WHERE role = 'member';

-- 3. Drop legacy role column from users
ALTER TABLE users DROP COLUMN role;
