-- ============================================================================
-- B2B DOMAIN MODULE (Projects, Tasks)
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS domain;

-- PROJECTS
CREATE TABLE IF NOT EXISTS domain.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    team_id UUID NOT NULL REFERENCES b2b.teams(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'archived')),
    created_by UUID NOT NULL REFERENCES b2b.users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_projects_tenant_id ON domain.projects(tenant_id);

-- TASKS
CREATE TABLE IF NOT EXISTS domain.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES domain.projects(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'todo' NOT NULL CHECK (status IN ('todo', 'in_progress', 'done')),
    assigned_to UUID REFERENCES b2b.users(id),
    due_date DATE,
    created_by UUID NOT NULL REFERENCES b2b.users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON domain.tasks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tasks_search ON domain.tasks USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- COMMENTS
CREATE TABLE IF NOT EXISTS domain.comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES domain.tasks(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    parent_comment_id UUID REFERENCES domain.comments(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES b2b.users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_comments_tenant_id ON domain.comments(tenant_id);

-- RLS
ALTER TABLE domain.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain.comments ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_projects ON domain.projects
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

CREATE POLICY tenant_isolation_tasks ON domain.tasks
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

CREATE POLICY tenant_isolation_comments ON domain.comments
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));
