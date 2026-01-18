-- ============================================================================
-- CONSOLIDATE ENRON SCHEMA INTO BANK SURVEILLANCE
-- ============================================================================
-- Moves enron_emails table from b2b_enron to bank_surveillance schema
-- Drops b2b_enron schema
-- Note: b2b_domain_api service restart required
-- ============================================================================

DO $$
BEGIN
    -- 1. Create bank_surveillance schema if not exists (should be there from 016)
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'bank_surveillance') THEN
        CREATE SCHEMA bank_surveillance;
    END IF;

    -- 2. Move enron_emails table if it sits in b2b_enron
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'b2b_enron' AND table_name = 'enron_emails') THEN
        -- Check if table already exists in destination (conflict safety)
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'bank_surveillance' AND table_name = 'enron_emails') THEN
            ALTER TABLE b2b_enron.enron_emails SET SCHEMA bank_surveillance;
        END IF;
    END IF;

    -- 3. Drop b2b_enron schema if exists
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'b2b_enron') THEN
        DROP SCHEMA b2b_enron CASCADE;
    END IF;
    
    -- 4. Ensure Permissions
    -- Grant usage to the schema for the app user (saas_demo_user usually in dev)
    -- We grant to PUBLIC or specific role if needed, but safe to grant to current user flow
    -- Assuming this runs as superuser, we grant to the app user (if different)
    -- But in docker-compose, migration might run as postgres.
END
$$;

-- 5. RLS Policies for enron_emails (if not already enabled)
ALTER TABLE bank_surveillance.enron_emails ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_enron_emails ON bank_surveillance.enron_emails;

CREATE POLICY tenant_isolation_enron_emails ON bank_surveillance.enron_emails
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        OR
        tenant_id IS NULL -- Global Enron data might be NULL tenant if public?
        -- If enron data is global/public dataset, we might want to allow all?
        -- For now, strict tenant isolation unless tenant_id is NULL.
    );
