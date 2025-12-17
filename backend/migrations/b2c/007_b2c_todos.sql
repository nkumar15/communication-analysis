-- B2C Todos Module
-- Implements the "Workspace Container" pattern where this domain is isolated in its own schema
-- but links securely to the core workspace infrastructure.

CREATE SCHEMA IF NOT EXISTS b2c_todos;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Todo Items Table
CREATE TABLE b2c_todos.items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES b2c.workspaces(id) ON DELETE CASCADE,
    
    title TEXT NOT NULL,
    description TEXT,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    due_date TIMESTAMP WITH TIME ZONE,
    
    created_by UUID REFERENCES b2c.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_b2c_todos_workspace ON b2c_todos.items(workspace_id);
CREATE INDEX idx_b2c_todos_created_by ON b2c_todos.items(created_by);

-- RLS: Enable Security
ALTER TABLE b2c_todos.items ENABLE ROW LEVEL SECURITY;

-- RLS Policy: View/Edit Access
-- "Users can access todos if they are a member of the linked workspace"
CREATE POLICY todo_access_policy ON b2c_todos.items
    USING (
        workspace_id IN (
            SELECT b2c.get_user_workspace_ids(NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        )
    )
    WITH CHECK (
        workspace_id IN (
            SELECT b2c.get_user_workspace_ids(NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        )
    );

-- Trigger for updated_at
CREATE TRIGGER update_b2c_todos_modtime
    BEFORE UPDATE ON b2c_todos.items
    FOR EACH ROW EXECUTE PROCEDURE update_modified_column();
