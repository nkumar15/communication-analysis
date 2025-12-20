-- ============================================================================
-- B2C CORE SCHEMA
-- ============================================================================
-- Foundation: Schema, Users, Workspaces, Members, and Core Functions.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS b2c;

-- ============================================================================
-- 1. COMMON TYPES & FUNCTIONS
-- ============================================================================

-- Workspace Type Enum
DO $$ BEGIN
    CREATE TYPE b2c.workspace_type AS ENUM ('personal', 'team');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Update Timestamp Trigger Function
CREATE OR REPLACE FUNCTION b2c.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Generic update_modified_column (used by some modules)
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 2. CORE TABLES
-- ============================================================================

-- USERS
CREATE TABLE b2c.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    avatar_url VARCHAR(500),
    email_verified BOOLEAN DEFAULT false,
    default_workspace_id UUID, -- Set after workspace creation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_b2c_users_firebase_uid ON b2c.users(firebase_uid);
CREATE INDEX idx_b2c_users_email ON b2c.users(email);

-- WORKSPACES
CREATE TABLE b2c.workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type b2c.workspace_type NOT NULL,
    owner_id UUID NOT NULL REFERENCES b2c.users(id) ON DELETE CASCADE,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_b2c_workspaces_owner ON b2c.workspaces(owner_id);
CREATE INDEX idx_b2c_workspaces_type ON b2c.workspaces(type);

-- Constraint for Users -> Default Workspace
ALTER TABLE b2c.users 
    ADD CONSTRAINT fk_users_default_workspace 
    FOREIGN KEY (default_workspace_id) 
    REFERENCES b2c.workspaces(id) 
    ON DELETE SET NULL;

-- WORKSPACE MEMBERS
CREATE TABLE b2c.workspace_members (
    workspace_id UUID REFERENCES b2c.workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES b2c.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    invited_by UUID REFERENCES b2c.users(id),
    PRIMARY KEY (workspace_id, user_id)
);

CREATE INDEX idx_b2c_workspace_members_user ON b2c.workspace_members(user_id);
CREATE INDEX idx_b2c_workspace_members_workspace ON b2c.workspace_members(workspace_id);

-- ============================================================================
-- 3. HELPER FUNCTIONS
-- ============================================================================

-- Function: Get User Workspaces (Prevent RLS Recursion)
CREATE OR REPLACE FUNCTION b2c.get_user_workspace_ids(uid UUID)
RETURNS TABLE (workspace_id UUID) 
SECURITY DEFINER
SET search_path = b2c, public
AS $$
BEGIN
    RETURN QUERY SELECT wm.workspace_id FROM b2c.workspace_members wm WHERE wm.user_id = uid;
END;
$$ LANGUAGE plpgsql;
ALTER FUNCTION b2c.get_user_workspace_ids(uuid) OWNER TO postgres;

-- Function: Lookup User by Firebase UID (Allows Deleted Users for 404 handling)
CREATE OR REPLACE FUNCTION b2c.lookup_user_by_firebase_uid(f_uid TEXT)
RETURNS UUID
SECURITY DEFINER
SET search_path = b2c, public
AS $$
BEGIN
    RETURN (SELECT id FROM b2c.users WHERE firebase_uid = f_uid);
END;
$$ LANGUAGE plpgsql;

-- Function: Lookup User by Email
CREATE OR REPLACE FUNCTION b2c.lookup_user_by_email(email_addr TEXT)
RETURNS UUID
SECURITY DEFINER
SET search_path = b2c, public
AS $$
BEGIN
    RETURN (SELECT id FROM b2c.users WHERE email = email_addr);
END;
$$ LANGUAGE plpgsql;
ALTER FUNCTION b2c.lookup_user_by_email(text) OWNER TO postgres;

-- ============================================================================
-- 4. RLS POLICIES (Core)
-- ============================================================================

-- ENABLE RLS
ALTER TABLE b2c.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2c.workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2c.workspace_members ENABLE ROW LEVEL SECURITY;

-- User Self Access
CREATE POLICY user_self_access ON b2c.users
    USING (id = NULLIF(current_setting('app.current_user_id', true), '')::uuid);

-- Workspace Access
CREATE POLICY workspace_member_access ON b2c.workspaces
    USING (
        owner_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        OR
        id IN (SELECT b2c.get_user_workspace_ids(NULLIF(current_setting('app.current_user_id', true), '')::uuid))
    );

-- Workspace Members Access
CREATE POLICY workspace_member_visibility ON b2c.workspace_members
    USING (
        user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        OR
        workspace_id IN (SELECT b2c.get_user_workspace_ids(NULLIF(current_setting('app.current_user_id', true), '')::uuid))
    );
