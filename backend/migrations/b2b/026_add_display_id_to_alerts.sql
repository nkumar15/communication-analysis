-- Add display_id column to alerts table
ALTER TABLE bank_surveillance.alerts ADD COLUMN IF NOT EXISTS display_id VARCHAR(20);

-- Create unique index for display_id
CREATE UNIQUE INDEX IF NOT EXISTS ix_alerts_display_id ON bank_surveillance.alerts (display_id);
