-- Migration 028: Add data_region_id and sensitivity_level_id to bank_surveillance.alerts
-- Denormalized from source communication so scoping never requires a JOIN.

ALTER TABLE bank_surveillance.alerts
    ADD COLUMN IF NOT EXISTS data_region_id    UUID REFERENCES b2b.geographic_regions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS sensitivity_level_id UUID REFERENCES b2b.sensitivity_levels(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_alerts_data_region_id
    ON bank_surveillance.alerts (data_region_id);

-- Backfill existing alerts from their linked communication
UPDATE bank_surveillance.alerts a
SET
    data_region_id        = c.data_region_id,
    sensitivity_level_id  = c.sensitivity_level_id
FROM bank_surveillance.communications c
WHERE a.communication_id = c.id
  AND a.data_region_id IS NULL;
