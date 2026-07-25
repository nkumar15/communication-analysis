-- Migration 030: Add region_id to b2b.teams
-- Links each team to a GeographicRegion so the geographic_boundaries plugin
-- can derive a user's geographic_scopes from their accessible_teams.

ALTER TABLE b2b.teams
    ADD COLUMN IF NOT EXISTS region_id UUID REFERENCES b2b.geographic_regions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_teams_region_id ON b2b.teams (region_id);
