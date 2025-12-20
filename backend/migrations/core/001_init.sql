-- Core Migration 001: Initialize Migration Tracking
-- This is always run first, regardless of which products are enabled

-- Create migration tracking table in public schema
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    filename VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Note: Individual schemas (platform, b2b, b2c) are created by their respective migrations
