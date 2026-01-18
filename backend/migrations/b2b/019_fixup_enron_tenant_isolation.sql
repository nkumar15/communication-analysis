-- ============================================================================
-- FIXUP: Add tenant isolation to enron_emails
-- ============================================================================
-- Addresses audit finding: bank_surveillance.enron_emails missing tenant_id and RLS
-- ============================================================================

-- 1. Add tenant_id column (nullable first for existing data)
ALTER TABLE bank_surveillance.enron_emails 
ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES b2b.tenants(id) ON DELETE CASCADE;

-- 2. Add index for tenant lookups
CREATE INDEX IF NOT EXISTS idx_enron_emails_tenant_id 
ON bank_surveillance.enron_emails(tenant_id);

-- 3. Enable Row Level Security
ALTER TABLE bank_surveillance.enron_emails ENABLE ROW LEVEL SECURITY;

-- 4. Create isolation policy
DROP POLICY IF EXISTS enron_emails_isolation_policy ON bank_surveillance.enron_emails;
CREATE POLICY enron_emails_isolation_policy ON bank_surveillance.enron_emails
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
