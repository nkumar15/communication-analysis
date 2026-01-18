ALTER TABLE bank_surveillance.enron_emails 
ADD COLUMN IF NOT EXISTS tenant_id UUID;

CREATE INDEX IF NOT EXISTS idx_enron_emails_tenant_id ON bank_surveillance.enron_emails(tenant_id);
