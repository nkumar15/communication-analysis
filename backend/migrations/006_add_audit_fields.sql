-- Migration: Add audit fields for security tracking
-- Date: 2025-11-26
-- Description: Add audit fields to invitations table for tracking acceptance
--              Add activation_started_at to tenants table for single-use token enforcement

-- Add audit fields to invitations table
ALTER TABLE invitations 
  ADD COLUMN IF NOT EXISTS accepted_by UUID REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS accepted_from_ip VARCHAR(45);

-- Add activation start tracking to tenants table
ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS activation_started_at TIMESTAMPTZ;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_invitations_accepted_by ON invitations(accepted_by);
CREATE INDEX IF NOT EXISTS idx_tenants_activation_started ON tenants(activation_started_at);

-- Add comments for documentation
COMMENT ON COLUMN invitations.accepted_by IS 'User ID who accepted the invitation (for audit trail)';
COMMENT ON COLUMN invitations.accepted_from_ip IS 'IP address from which invitation was accepted';
COMMENT ON COLUMN tenants.activation_started_at IS 'Timestamp when activation process started (prevents replay attacks)';
