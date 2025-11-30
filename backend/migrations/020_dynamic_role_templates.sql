-- ============================================================================
-- Dynamic Role Templates
-- ============================================================================

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
-- Seed Default Templates
-- ============================================================================

INSERT INTO b2b.role_templates (name, display_name, description, is_system_role, is_default, permissions) VALUES
(
    'owner', 
    'Owner', 
    'Primary administrator with total control over account, billing, security, and users', 
    TRUE, 
    TRUE,
    '[
        {"resource": "dashboard", "actions": ["read"]},
        {"resource": "users", "actions": ["read", "write", "delete", "invite"]},
        {"resource": "roles", "actions": ["read", "write"]}
    ]'::jsonb
),
(
    'admin', 
    'Admin', 
    'Administrator with management and configuration capabilities', 
    TRUE, 
    TRUE,
    '[
        {"resource": "dashboard", "actions": ["read"]},
        {"resource": "users", "actions": ["read", "write", "invite"]},
        {"resource": "roles", "actions": ["read", "write"]}
    ]'::jsonb
),
(
    'viewer', 
    'Viewer', 
    'Read-only access to content, reports, and dashboards', 
    TRUE, 
    TRUE,
    '[
        {"resource": "dashboard", "actions": ["read"]},
        {"resource": "users", "actions": ["read"]},
        {"resource": "roles", "actions": ["read"]}
    ]'::jsonb
)
ON CONFLICT (name) DO UPDATE SET
    permissions = EXCLUDED.permissions,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    is_default = EXCLUDED.is_default;
