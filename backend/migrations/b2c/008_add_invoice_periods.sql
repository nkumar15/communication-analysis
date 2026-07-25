-- ============================================================================
-- B2C INVOICE BILLING PERIODS
-- ============================================================================
-- Add billing period columns for invoice date ranges
-- ============================================================================

-- Add billing period columns to B2C invoices
ALTER TABLE b2c.invoices ADD COLUMN billing_period_start TIMESTAMP(6) WITH TIME ZONE;
ALTER TABLE b2c.invoices ADD COLUMN billing_period_end TIMESTAMP(6) WITH TIME ZONE;
