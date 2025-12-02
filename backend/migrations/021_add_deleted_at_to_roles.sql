-- Add deleted_at column to roles table for soft delete support
ALTER TABLE b2b.roles ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;

-- Add index for performance when filtering non-deleted roles
CREATE INDEX idx_roles_deleted_at ON b2b.roles(deleted_at) WHERE deleted_at IS NULL;
