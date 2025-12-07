
-- ============================================================================
-- Dynamic Role Templates (SaaS Boilerplate)
-- ============================================================================
-- These are the default role templates that every tenant gets.
-- Best practices for SaaS role permissions:
--   - Owner: Full control (billing, security, all features)
--   - Admin: Management capabilities (no billing/account deletion)
--   - Viewer: Read-only access

CREATE TABLE IF NOT EXISTS b2b.role_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_role_templates_is_default ON b2b.role_templates(is_default);

-- ============================================================================
-- Seed Default Templates (SaaS Best Practices)
-- ============================================================================

INSERT INTO b2b.role_templates (name, display_name, description, is_system_role, is_default, permissions) VALUES
(
    'owner', 
    'Owner', 
    'Primary administrator with total control over account, billing, security, and all features', 
    TRUE, 
    TRUE,
    '[
        {"resource": "dashboard", "actions": ["read"]},
        {"resource": "reports", "actions": ["read", "export"]},
        {"resource": "analytics", "actions": ["read"]},
        
        {"resource": "users", "actions": ["read", "write", "delete", "invite"]},
        {"resource": "roles", "actions": ["read", "write", "delete"]},
        {"resource": "invitations", "actions": ["read", "write", "delete"]},
        {"resource": "teams", "actions": ["read", "write", "delete"]},
        
        {"resource": "account", "actions": ["read", "write", "delete"]},
        {"resource": "billing", "actions": ["read", "write", "manage"]},
        {"resource": "invoices", "actions": ["read", "export"]},
        
        {"resource": "integrations", "actions": ["read", "write", "delete"]},
        {"resource": "webhooks", "actions": ["read", "write", "delete"]},
        {"resource": "api_keys", "actions": ["read", "write", "delete"]},
        
        {"resource": "audit_logs", "actions": ["read", "export"]},
        {"resource": "security", "actions": ["read", "write", "manage"]},
        
        {"resource": "support", "actions": ["read", "write"]},
        {"resource": "notifications", "actions": ["read", "write"]}
    ]'::jsonb
),
(
    'admin', 
    'Admin', 
    'Administrator with management capabilities, but no billing or account deletion access', 
    TRUE, 
    TRUE,
    '[
        {"resource": "dashboard", "actions": ["read"]},
        {"resource": "reports", "actions": ["read", "export"]},
        {"resource": "analytics", "actions": ["read"]},
        
        {"resource": "users", "actions": ["read", "write", "invite"]},
        {"resource": "roles", "actions": ["read", "write"]},
        {"resource": "invitations", "actions": ["read", "write"]},
        {"resource": "teams", "actions": ["read", "write"]},
        
        {"resource": "account", "actions": ["read"]},
        {"resource": "billing", "actions": ["read"]},
        {"resource": "invoices", "actions": ["read"]},
        
        {"resource": "integrations", "actions": ["read", "write"]},
        {"resource": "webhooks", "actions": ["read", "write"]},
        {"resource": "api_keys", "actions": ["read", "write"]},
        
        {"resource": "audit_logs", "actions": ["read"]},
        {"resource": "security", "actions": ["read"]},
        
        {"resource": "support", "actions": ["read", "write"]},
        {"resource": "notifications", "actions": ["read", "write"]}
    ]'::jsonb
),
(
    'viewer', 
    'Viewer', 
    'Read-only access to dashboards, reports, and non-sensitive information', 
    TRUE, 
    TRUE,
    '[
        {"resource": "dashboard", "actions": ["read"]},
        {"resource": "reports", "actions": ["read"]},
        {"resource": "analytics", "actions": ["read"]},
        
        {"resource": "users", "actions": ["read"]},
        {"resource": "roles", "actions": ["read"]},
        {"resource": "teams", "actions": ["read"]},
        
        {"resource": "notifications", "actions": ["read", "write"]}
    ]'::jsonb
),
(
    'team_manager',
    'Team Manager',
    'Full control over team membership and settings',
    FALSE,
    TRUE,
    '[
        {"resource": "team_members", "actions": ["read", "write", "delete", "invite"]},
        {"resource": "team_settings", "actions": ["read", "write"]}
    ]'::jsonb
),
(
    'team_member',
    'Team Member',
    'Active team participant with standard access',
    FALSE,
    TRUE,
    '[
        {"resource": "team_members", "actions": ["read"]},
        {"resource": "team_settings", "actions": ["read"]}
    ]'::jsonb
),
(
    'team_viewer',
    'Team Viewer',
    'Read-only access to team information',
    FALSE,
    TRUE,
    '[
        {"resource": "team_members", "actions": ["read"]},
        {"resource": "team_settings", "actions": ["read"]}
    ]'::jsonb
)
ON CONFLICT (name) DO UPDATE SET
    permissions = EXCLUDED.permissions,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    is_default = EXCLUDED.is_default;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE b2b.role_templates IS 'Global role templates used to seed tenant roles';
COMMENT ON COLUMN b2b.role_templates.is_default IS 'Default templates are automatically seeded for new tenants';
COMMENT ON COLUMN b2b.role_templates.permissions IS 'JSONB array of {resource, actions[]} defining permissions';


-- ============================================================================
-- B2B RBAC SYSTEM: Roles, Resources, Actions, Permissions (SaaS Boilerplate)
-- ============================================================================
-- IMPORTANT: This creates RBAC tables in the b2b schema (not public).
-- Platform and B2C will have their own RBAC systems in their respective schemas.
-- 
-- This is domain-agnostic SaaS boilerplate. Domain-specific resources (shops, etc)
-- should be seeded via backend/scripts/b2b/seed_domain_data.py
-- ============================================================================

-- ============================================================================
-- B2B RBAC CORE TABLES (in b2b schema)
-- ============================================================================

-- Roles table (tenant-scoped)
CREATE TABLE IF NOT EXISTS b2b.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,                  -- Internal name: 'owner', 'admin', 'viewer'
    display_name VARCHAR(100) NOT NULL,         -- UI name: 'Owner', 'Admin', 'Viewer'
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,       -- Cannot be deleted
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT unique_tenant_role_name UNIQUE(tenant_id, name)
);

-- Resources table (application-wide, reusable across tenants)
CREATE TABLE IF NOT EXISTS b2b.resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,           -- 'dashboard', 'users', 'billing'
    display_name VARCHAR(100) NOT NULL,         -- 'Dashboard', 'User Management'
    category VARCHAR(50),                        -- Group in UI: 'Administration', 'Security'
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT unique_resource_name UNIQUE(name)
);

-- Actions table (generic, reusable)
CREATE TABLE IF NOT EXISTS b2b.actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,                  -- 'read', 'write', 'delete', 'invite'
    display_name VARCHAR(100) NOT NULL,         -- 'View', 'Create/Edit', 'Delete'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT unique_action_name UNIQUE(name)
);

-- Role Permissions (maps roles to resource+action combinations)
CREATE TABLE IF NOT EXISTS b2b.role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES b2b.roles(id) ON DELETE CASCADE,
    resource_id UUID NOT NULL REFERENCES b2b.resources(id) ON DELETE CASCADE,
    action_id UUID NOT NULL REFERENCES b2b.actions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT unique_role_resource_action UNIQUE(role_id, resource_id, action_id)
);

-- ============================================================================
-- UPDATE B2B USERS TABLE WITH RBAC FOREIGN KEYS
-- ============================================================================

-- Add foreign key constraint to users.role_id (column already exists from 001_schema.sql)
ALTER TABLE b2b.users ADD CONSTRAINT fk_users_role_id 
    FOREIGN KEY (role_id) REFERENCES b2b.roles(id);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_roles_tenant_id ON b2b.roles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_roles_name ON b2b.roles(name);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON b2b.role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_resource_id ON b2b.role_permissions(resource_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_action_id ON b2b.role_permissions(action_id);

-- ============================================================================
-- SEED DATA: ACTIONS (Universal across all SaaS)
-- ============================================================================

INSERT INTO b2b.actions (name, display_name) VALUES
    ('read', 'View'),
    ('write', 'Create/Edit'),
    ('delete', 'Delete'),
    ('invite', 'Invite Users'),
    ('export', 'Export Data'),
    ('manage', 'Full Management')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- SEED DATA: RESOURCES (SaaS Boilerplate - Domain Agnostic)
-- ============================================================================
-- Common resources found in any multi-tenant SaaS application
-- Domain-specific resources (shops) should be added via Python seed scripts

INSERT INTO b2b.resources (name, display_name, category, description) VALUES
    -- Analytics & Reporting
    ('dashboard', 'Dashboard', 'Analytics', 'Statistics, metrics, and overview'),
    ('reports', 'Reports', 'Analytics', 'Generate and view business reports'),
    ('analytics', 'Analytics', 'Analytics', 'Advanced analytics and insights'),
    
    -- User & Access Management  
    ('users', 'User Management', 'Administration', 'Manage users and team members'),
    ('roles', 'Role Management', 'Administration', 'Manage roles and permissions'),
    ('invitations', 'Invitations', 'Administration', 'Invite new users to the platform'),
    ('teams', 'Team Management', 'Administration', 'Organize users into teams'),
    ('team_members', 'Team Members', 'Team Management', 'Manage team membership'),
    ('team_settings', 'Team Settings', 'Team Management', 'Configure team settings'),
    
    -- Account & Billing
    ('account', 'Account Settings', 'Configuration', 'Manage account configuration and preferences'),
    ('billing', 'Billing & Subscription', 'Administration', 'Manage billing, payments, and subscription plans'),
    ('invoices', 'Invoices', 'Billing', 'View and download invoices'),
    
    -- Integration & API
    ('integrations', 'Integrations', 'Configuration', 'Third-party integrations and connections'),
    ('webhooks', 'Webhooks', 'Configuration', 'Configure outbound webhooks'),
    ('api_keys', 'API Keys', 'Security', 'Manage API keys and access tokens'),
    
    -- Audit & Security
    ('audit_logs', 'Audit Logs', 'Security', 'View system audit logs and user activity'),
    ('security', 'Security Settings', 'Security', 'Manage security policies and two-factor authentication'),
    
    -- Support & Documentation
    ('support', 'Support', 'Help', 'Access support tickets and help resources'),
    ('notifications', 'Notifications', 'Configuration', 'Manage notification preferences')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- SOFT DELETE SUPPORT
-- ============================================================================
-- (Consolidated from migration 021)

ALTER TABLE b2b.roles ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;

-- Add partial index for performance when filtering non-deleted roles
CREATE INDEX idx_roles_deleted_at ON b2b.roles(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE b2b.roles IS 'B2B tenant-specific roles with customizable permissions';
COMMENT ON TABLE b2b.resources IS 'B2B SaaS boilerplate resources - domain-agnostic, reusable across tenants';
COMMENT ON TABLE b2b.actions IS 'B2B generic actions that can be performed on resources';
COMMENT ON TABLE b2b.role_permissions IS 'B2B role-to-resource+action mappings';

COMMENT ON COLUMN b2b.roles.name IS 'Internal role identifier (lowercase, no spaces)';
COMMENT ON COLUMN b2b.roles.display_name IS 'Human-readable role name shown in UI';
COMMENT ON COLUMN b2b.roles.is_system_role IS 'System roles cannot be deleted by users';
COMMENT ON COLUMN b2b.roles.deleted_at IS 'Soft delete timestamp - role is hidden when set';
