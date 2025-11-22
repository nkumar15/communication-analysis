-- Add tenant activation fields for onboarding workflow
-- This enables white-glove tenant provisioning with magic link activation

-- Add activation fields to tenants table
ALTER TABLE tenants ADD COLUMN activation_token VARCHAR(64) UNIQUE;
ALTER TABLE tenants ADD COLUMN activation_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE tenants ADD COLUMN activation_expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE tenants ADD COLUMN activated_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE tenants ADD COLUMN activated_by INTEGER REFERENCES users(id);

-- Add role field to users table for RBAC
ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'member';

-- Create indexes for performance
CREATE INDEX idx_tenants_activation_status ON tenants(activation_status);
CREATE INDEX idx_tenants_activation_token ON tenants(activation_token);
CREATE INDEX idx_users_role ON users(role);

-- Add comments for documentation
COMMENT ON COLUMN tenants.activation_token IS 'Single-use token for tenant activation (48-hour expiry)';
COMMENT ON COLUMN tenants.activation_status IS 'Status: pending, active, expired';
COMMENT ON COLUMN tenants.activation_expires_at IS 'Token expiry timestamp (48 hours from creation)';
COMMENT ON COLUMN tenants.activated_at IS 'Timestamp when tenant was activated';
COMMENT ON COLUMN tenants.activated_by IS 'User ID who completed activation';
COMMENT ON COLUMN users.role IS 'User role: admin, manager, member';

-- Set existing tenants to active (backward compatibility)
UPDATE tenants SET activation_status = 'active' WHERE activation_status = 'pending';
