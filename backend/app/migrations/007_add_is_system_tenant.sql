-- Add is_system_tenant column to tenants table
ALTER TABLE tenants ADD COLUMN is_system_tenant BOOLEAN DEFAULT FALSE;

-- Create index for faster lookups
CREATE INDEX idx_tenants_is_system_tenant ON tenants(is_system_tenant);

-- Mark the existing system tenant as system tenant
UPDATE tenants SET is_system_tenant = TRUE WHERE name = 'SaaS Platform System';
