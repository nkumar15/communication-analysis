-- Migration 014: Create B2C Workspace Tables
-- Creates B2C workspace structure for personal and team workspaces

-- Create workspaces table
CREATE TABLE b2c.workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('personal', 'team')),
    owner_id UUID NOT NULL,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create workspace members table (for team workspaces)
CREATE TABLE b2c.workspace_members (
    workspace_id UUID REFERENCES b2c.workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);

-- Create B2C users table (separate from B2B tenant users)
CREATE TABLE b2c.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    firebase_uid VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    default_workspace_id UUID REFERENCES b2c.workspaces(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_workspaces_owner ON b2c.workspaces(owner_id);
CREATE INDEX idx_workspace_members_user ON b2c.workspace_members(user_id);
CREATE INDEX idx_users_firebase ON b2c.users(firebase_uid);
CREATE INDEX idx_users_email ON b2c.users(email);

-- Enable Row-Level Security
ALTER TABLE b2c.workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2c.workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2c.users ENABLE ROW LEVEL SECURITY;

-- Workspace isolation: Users can only see workspaces they own or are members of
CREATE POLICY workspace_access ON b2c.workspaces
    USING (
        owner_id::text = current_setting('app.current_user_id', true)
        OR id IN (
            SELECT workspace_id FROM b2c.workspace_members 
            WHERE user_id::text = current_setting('app.current_user_id', true)
        )
    );

-- Member access: Users can only see members of workspaces they belong to
CREATE POLICY member_access ON b2c.workspace_members
    USING (
        workspace_id IN (
            SELECT id FROM b2c.workspaces 
            WHERE owner_id::text = current_setting('app.current_user_id', true)
        )
        OR workspace_id IN (
            SELECT workspace_id FROM b2c.workspace_members 
            WHERE user_id::text = current_setting('app.current_user_id', true)
        )
    );

-- User access: Users can only see their own record
CREATE POLICY user_self_access ON b2c.users
    USING (id::text = current_setting('app.current_user_id', true));

-- Verify tables created
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'b2c' AND table_name = 'workspaces'
    ) THEN
        RAISE EXCEPTION 'Table b2c.workspaces not created';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'b2c' AND table_name = 'workspace_members'
    ) THEN
        RAISE EXCEPTION 'Table b2c.workspace_members not created';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'b2c' AND table_name = 'users'
    ) THEN
        RAISE EXCEPTION 'Table b2c.users not created';
    END IF;
    
    RAISE NOTICE 'All B2C tables created successfully';
END $$;
