BEGIN;

-- Add display_id column to cases table for human-readable IDs (e.g., CAS-12345)
ALTER TABLE bank_surveillance.cases 
ADD COLUMN IF NOT EXISTS display_id VARCHAR(20);

-- Ensure uniqueness for direct lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_cases_display_id ON bank_surveillance.cases(display_id);

COMMIT;
