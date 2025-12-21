-- Add billing period columns to B2C invoices
ALTER TABLE b2c.invoices ADD COLUMN billing_period_start TIMESTAMP(6) WITH TIME ZONE;
ALTER TABLE b2c.invoices ADD COLUMN billing_period_end TIMESTAMP(6) WITH TIME ZONE;
