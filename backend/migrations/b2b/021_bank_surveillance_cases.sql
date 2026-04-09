-- ============================================================================
-- CASE MANAGEMENT TABLES (Bank Surveillance)
-- ============================================================================

BEGIN;

-- 1. Rename existing investigations to cases for better alignment with "Case Management" feature
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'bank_surveillance' AND table_name = 'investigations') THEN
        ALTER TABLE bank_surveillance.investigations RENAME TO cases;
    END IF;
END $$;

-- 2. Add decision fields and SLA tracking to cases
ALTER TABLE bank_surveillance.cases 
ADD COLUMN IF NOT EXISTS target_closure_date TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS decision_rationale TEXT;

-- 3. Case Notes (Discussion Thread)
CREATE TABLE IF NOT EXISTS bank_surveillance.case_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES bank_surveillance.cases(id) ON DELETE CASCADE,
    author_id UUID REFERENCES b2b.users(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 4. Case Evidence (Linked Communications/Alerts)
CREATE TABLE IF NOT EXISTS bank_surveillance.case_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES bank_surveillance.cases(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL, -- 'communication', 'alert'
    evidence_id UUID NOT NULL, -- Polymorphic reference
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 5. Row-Level Security
ALTER TABLE bank_surveillance.cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_surveillance.case_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_surveillance.case_evidence ENABLE ROW LEVEL SECURITY;

-- Refresh policy for renamed table
DROP POLICY IF EXISTS tenant_isolation_investigations ON bank_surveillance.cases;
DROP POLICY IF EXISTS tenant_isolation_cases ON bank_surveillance.cases;
CREATE POLICY tenant_isolation_cases ON bank_surveillance.cases
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

-- Notes isolation
DROP POLICY IF EXISTS tenant_isolation_case_notes ON bank_surveillance.case_notes;
CREATE POLICY tenant_isolation_case_notes ON bank_surveillance.case_notes
    FOR ALL
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        EXISTS (
            SELECT 1 FROM bank_surveillance.cases c
            WHERE c.id = bank_surveillance.case_notes.case_id 
            AND c.tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    );

-- Evidence isolation
DROP POLICY IF EXISTS tenant_isolation_case_evidence ON bank_surveillance.case_evidence;
CREATE POLICY tenant_isolation_case_evidence ON bank_surveillance.case_evidence
    FOR ALL
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        EXISTS (
            SELECT 1 FROM bank_surveillance.cases c
            WHERE c.id = bank_surveillance.case_evidence.case_id 
            AND c.tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    );

-- 6. Indexes
CREATE INDEX IF NOT EXISTS idx_case_notes_case_id ON bank_surveillance.case_notes(case_id);
CREATE INDEX IF NOT EXISTS idx_case_evidence_case_id ON bank_surveillance.case_evidence(case_id);
CREATE INDEX IF NOT EXISTS idx_case_evidence_polymorphic ON bank_surveillance.case_evidence(evidence_type, evidence_id);

COMMIT;
