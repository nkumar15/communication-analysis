-- Create ingestion_logs table
CREATE TABLE IF NOT EXISTS bank_surveillance.ingestion_logs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date VARCHAR(8) NOT NULL,
    status VARCHAR(50) DEFAULT 'running',
    file_path VARCHAR(255) NOT NULL,
    processed_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_ingestion_logs_date ON bank_surveillance.ingestion_logs(date);
CREATE INDEX IF NOT EXISTS idx_ingestion_logs_status ON bank_surveillance.ingestion_logs(status);
