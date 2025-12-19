-- Migration: Make Platform Roles System-Level (Remove Tenant FK)
-- Purpose: Platform roles are system-level and should not be tied to specific tenants

-- Drop the foreign key constraint
ALTER TABLE platform.platform_roles 
DROP CONSTRAINT IF EXISTS platform_roles_platform_tenant_id_fkey;

-- Drop the index
DROP INDEX IF EXISTS platform.idx_platform_roles_tenant;

-- Drop the column
ALTER TABLE platform.platform_roles 
DROP COLUMN IF EXISTS platform_tenant_id;

-- Add comment
COMMENT ON TABLE platform.platform_roles IS 'System-level platform roles (platform_admin, support_staff, etc.) - independent of tenants';
