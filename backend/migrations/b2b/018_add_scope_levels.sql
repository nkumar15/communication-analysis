-- ============================================================================
-- B2B ORGANIZATIONAL TIERS
-- ============================================================================
-- Database-driven org tier support (GLOBAL, REGIONAL, COUNTRY, BRANCH)
-- ============================================================================

-- Migration: Add Organizational Tier Support (Database-Driven)
-- Creates org_tiers table and references it from teams and team_role_definitions

-- Create org_tiers reference table
CREATE TABLE IF NOT EXISTS b2b.org_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(20) NOT NULL UNIQUE,
    display_name VARCHAR(50) NOT NULL,
    description TEXT,
    hierarchy_order INTEGER NOT NULL DEFAULT 0,  -- Lower = broader scope (GLOBAL=1, BRANCH=4)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE b2b.org_tiers IS 'Reference table for organizational tiers (GLOBAL, REGIONAL, COUNTRY, BRANCH)';
COMMENT ON COLUMN b2b.org_tiers.hierarchy_order IS 'Hierarchy order: 1=GLOBAL (broadest), 4=BRANCH (narrowest)';

-- Add org_tier_id FK to teams table (nullable for backward compatibility)
ALTER TABLE b2b.teams
ADD COLUMN IF NOT EXISTS org_tier_id UUID REFERENCES b2b.org_tiers(id);

-- Keep the org_tier VARCHAR for backward compatibility / denormalization
ALTER TABLE b2b.teams
ADD COLUMN IF NOT EXISTS org_tier VARCHAR(20);

-- Add allowed_org_tiers to team_role_definitions (stored as array of tier names)
ALTER TABLE b2b.team_role_definitions
ADD COLUMN IF NOT EXISTS allowed_org_tiers VARCHAR[] DEFAULT '{}';

COMMENT ON COLUMN b2b.team_role_definitions.allowed_org_tiers IS 'Array of org tier names this role can be assigned to';
