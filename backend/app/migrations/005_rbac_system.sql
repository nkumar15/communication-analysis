-- RBAC System Tables: Roles, Resources, Actions, Permissions
-- This enables database-driven permission management with hierarchical scoping

-- ============================================================================
-- CORE RBAC TABLES
-- ============================================================================

-- Roles table (tenant-scoped)
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,                  -- Internal name: 'admin', 'field_manager'
    display_name VARCHAR(100) NOT NULL,         -- UI name: 'Admin', 'Field Manager'
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,       -- Cannot be deleted
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_tenant_role_name UNIQUE(tenant_id, name)
);

-- Resources table (application-wide, reusable across tenants)
CREATE TABLE resources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,           -- 'dashboard', 'users', 'farmers'
    display_name VARCHAR(100) NOT NULL,         -- 'Dashboard', 'User Management'
    category VARCHAR(50),                        -- Group in UI: 'Administration', 'Core'
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_resource_name UNIQUE(name)
);

-- Actions table (generic, reusable)
CREATE TABLE actions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,                  -- 'read', 'write', 'delete', 'invite'
    display_name VARCHAR(100) NOT NULL,         -- 'View', 'Create/Edit', 'Delete'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_action_name UNIQUE(name)
);

-- Role Permissions (maps roles to resource+action combinations)
CREATE TABLE role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    action_id INTEGER NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_role_resource_action UNIQUE(role_id, resource_id, action_id)
);

-- ============================================================================
-- MODIFY EXISTING TABLES FOR RBAC
-- ============================================================================

-- Add role reference to users (replacing old role column later)
ALTER TABLE users ADD COLUMN role_id INTEGER REFERENCES roles(id);

-- Add reporting structure to users (for hierarchical scoping)
ALTER TABLE users ADD COLUMN invited_by INTEGER REFERENCES users(id);

-- Add role column to invitations (for migration compatibility)
-- Will be used to assign role when invitation is accepted
-- Already exists, no change needed

-- ============================================================================
-- FARMERS TABLE (Example Resource with Row-Level Security)
-- ============================================================================

CREATE TABLE farmers (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Farmer details
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    
    -- Row-level security (ownership tracking)
    created_by INTEGER NOT NULL REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Roles indexes
CREATE INDEX idx_roles_tenant_id ON roles(tenant_id);
CREATE INDEX idx_roles_name ON roles(name);

-- Role permissions indexes
CREATE INDEX idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX idx_role_permissions_resource_id ON role_permissions(resource_id);
CREATE INDEX idx_role_permissions_action_id ON role_permissions(action_id);

-- Users indexes (for hierarchical queries)
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_users_invited_by ON users(invited_by);

-- Farmers indexes
CREATE INDEX idx_farmers_tenant_id ON farmers(tenant_id);
CREATE INDEX idx_farmers_created_by ON farmers(created_by);
CREATE INDEX idx_farmers_email ON farmers(email);

-- ============================================================================
-- TABLE COMMENTS
-- ============================================================================

COMMENT ON TABLE roles IS 'Tenant-specific roles with customizable permissions';
COMMENT ON TABLE resources IS 'Application resources (features/modules) that can be controlled';
COMMENT ON TABLE actions IS 'Generic actions that can be performed on resources';
COMMENT ON TABLE role_permissions IS 'Maps roles to allowed resource+action combinations';
COMMENT ON TABLE farmers IS 'Farmer management with row-level security';

COMMENT ON COLUMN roles.name IS 'Internal role identifier (lowercase, no spaces)';
COMMENT ON COLUMN roles.display_name IS 'Human-readable role name shown in UI';
COMMENT ON COLUMN roles.is_system_role IS 'System roles cannot be deleted (admin, field_manager, field_agent)';

COMMENT ON COLUMN users.role_id IS 'User role for permission checking';
COMMENT ON COLUMN users.invited_by IS 'User who invited this user (for reporting hierarchy)';

COMMENT ON COLUMN farmers.created_by IS 'User who created this farmer record (for row-level access control)';
