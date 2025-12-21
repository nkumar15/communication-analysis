-- Migration: Add applicable_resources and description to actions table
-- This enables backend-driven action filtering per resource type

ALTER TABLE b2b.actions 
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS applicable_resources JSONB;

-- Add comment for documentation
COMMENT ON COLUMN b2b.actions.applicable_resources IS 'JSON array of resource names this action applies to. NULL means applies to all resources.';
COMMENT ON COLUMN b2b.actions.description IS 'Description of what this action does';
