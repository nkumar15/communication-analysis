-- ============================================================================
-- PROJECTS, TASKS & COMMENTS SYSTEM
-- ============================================================================
-- Generic task management system for B2B SaaS with:
-- - Projects: Containers for tasks, scoped to teams
-- - Tasks: Work items with simple status workflow
-- - Comments: Threaded discussions on tasks
--
-- Multi-tenant isolation via RLS policies
-- Team-scoped access control
-- ============================================================================

-- ============================================================================
-- PROJECTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS domain.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    team_id UUID NOT NULL REFERENCES b2b.teams(id) ON DELETE CASCADE,
    
    -- Project details
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'archived')),
    
    -- Ownership
    created_by UUID NOT NULL REFERENCES b2b.users(id),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

-- Indexes for projects
CREATE INDEX IF NOT EXISTS idx_projects_tenant_id ON domain.projects(tenant_id);
CREATE INDEX IF NOT EXISTS idx_projects_team_id ON domain.projects(team_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON domain.projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_created_by ON domain.projects(created_by);
CREATE INDEX IF NOT EXISTS idx_projects_deleted_at ON domain.projects(deleted_at) WHERE deleted_at IS NULL;

-- RLS for projects
ALTER TABLE domain.projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_projects ON domain.projects
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

COMMENT ON POLICY tenant_isolation_projects ON domain.projects IS 
    'Enforces tenant isolation for projects';

-- ============================================================================
-- TASKS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS domain.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES domain.projects(id) ON DELETE CASCADE,
    
    -- Task details
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'todo' NOT NULL CHECK (status IN ('todo', 'in_progress', 'done')),
    
    -- Assignment
    assigned_to UUID REFERENCES b2b.users(id),
    
    -- Dates
    due_date DATE,
    
    -- Ownership
    created_by UUID NOT NULL REFERENCES b2b.users(id),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

-- Indexes for tasks
CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON domain.tasks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON domain.tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON domain.tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON domain.tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON domain.tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_created_by ON domain.tasks(created_by);
CREATE INDEX IF NOT EXISTS idx_tasks_deleted_at ON domain.tasks(deleted_at) WHERE deleted_at IS NULL;

-- Full-text search on title and description
CREATE INDEX IF NOT EXISTS idx_tasks_search ON domain.tasks 
    USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- RLS for tasks
ALTER TABLE domain.tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_tasks ON domain.tasks
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

COMMENT ON POLICY tenant_isolation_tasks ON domain.tasks IS 
    'Enforces tenant isolation for tasks';

-- ============================================================================
-- COMMENTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS domain.comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES domain.tasks(id) ON DELETE CASCADE,
    
    -- Comment content
    content TEXT NOT NULL,
    
    -- Threading support (replies to comments)
    parent_comment_id UUID REFERENCES domain.comments(id) ON DELETE CASCADE,
    
    -- Ownership
    created_by UUID NOT NULL REFERENCES b2b.users(id),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

-- Indexes for comments
CREATE INDEX IF NOT EXISTS idx_comments_tenant_id ON domain.comments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_comments_task_id ON domain.comments(task_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON domain.comments(parent_comment_id);
CREATE INDEX IF NOT EXISTS idx_comments_created_by ON domain.comments(created_by);
CREATE INDEX IF NOT EXISTS idx_comments_deleted_at ON domain.comments(deleted_at) WHERE deleted_at IS NULL;

-- RLS for comments
ALTER TABLE domain.comments ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_comments ON domain.comments
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

COMMENT ON POLICY tenant_isolation_comments ON domain.comments IS 
    'Enforces tenant isolation for comments';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    -- Verify projects RLS
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'domain' 
    AND tablename = 'projects' 
    AND policyname = 'tenant_isolation_projects';
    
    IF policy_count = 0 THEN
        RAISE EXCEPTION 'RLS policy not found for domain.projects';
    END IF;
    
    -- Verify tasks RLS
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'domain' 
    AND tablename = 'tasks' 
    AND policyname = 'tenant_isolation_tasks';
    
    IF policy_count = 0 THEN
        RAISE EXCEPTION 'RLS policy not found for domain.tasks';
    END IF;
    
    -- Verify comments RLS
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'domain' 
    AND tablename = 'comments' 
    AND policyname = 'tenant_isolation_comments';
    
    IF policy_count = 0 THEN
        RAISE EXCEPTION 'RLS policy not found for domain.comments';
    END IF;
    
    RAISE NOTICE 'Projects, tasks, and comments RLS policies created successfully';
END $$;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE domain.projects IS 'Project management with team-scoped access and multi-tenant isolation';
COMMENT ON TABLE domain.tasks IS 'Tasks with simple workflow (todo/in_progress/done) and assignment tracking';
COMMENT ON TABLE domain.comments IS 'Threaded comments on tasks with parent-child relationships';

COMMENT ON COLUMN domain.projects.team_id IS 'Team that owns this project (team-scoped access)';
COMMENT ON COLUMN domain.projects.status IS 'Project status: active or archived';
COMMENT ON COLUMN domain.tasks.status IS 'Task status: todo, in_progress, or done';
COMMENT ON COLUMN domain.tasks.assigned_to IS 'User assigned to this task (must be team member)';
COMMENT ON COLUMN domain.comments.parent_comment_id IS 'Parent comment for threaded replies (NULL for top-level comments)';
