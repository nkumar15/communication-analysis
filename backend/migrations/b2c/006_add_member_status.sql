-- ============================================================================
-- B2C WORKSPACE MEMBER STATUS
-- ============================================================================
-- Add status column for member activation/suspension
-- ============================================================================

-- Add status column to workspace_members table
ALTER TABLE b2c.workspace_members ADD COLUMN status VARCHAR(20) DEFAULT 'active' NOT NULL;
