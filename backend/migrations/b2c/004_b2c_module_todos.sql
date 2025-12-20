-- ============================================================================
-- B2C TODOS (Example Module)
-- ============================================================================
-- Demonstrates how to add a module linked to B2C workspaces/users
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS b2c_todos;

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

CREATE TRIGGER update_b2c_todos_modtime
    BEFORE UPDATE ON b2c_todos.items
    FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

-- RLS
ALTER TABLE b2c_todos.items ENABLE ROW LEVEL SECURITY;

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
