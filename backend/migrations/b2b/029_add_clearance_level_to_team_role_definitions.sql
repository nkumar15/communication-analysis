-- Migration 029: Add clearance_level to b2b.team_role_definitions
-- Stores the minimum data clearance granted by a team role.
-- Scale: 0=PUBLIC, 1=INTERNAL, 2=CONFIDENTIAL, 3=RESTRICTED, 4=TOP_SECRET

ALTER TABLE b2b.team_role_definitions
    ADD COLUMN IF NOT EXISTS clearance_level INTEGER NOT NULL DEFAULT 1;

-- Seed sensible defaults for existing system roles
UPDATE b2b.team_role_definitions SET clearance_level = 1 WHERE is_system = TRUE AND clearance_level = 1;
