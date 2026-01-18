-- Create schema for Finance Trader domain
CREATE SCHEMA IF NOT EXISTS b2c_finance_trader;

-- Create rag_documents table
CREATE TABLE IF NOT EXISTS b2c_finance_trader.rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES b2c.workspaces(id) ON DELETE CASCADE,
    uploaded_by UUID REFERENCES b2c.users(id) ON DELETE SET NULL,
    
    -- File Details
    filename VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    content_hash VARCHAR(64) NOT NULL,
    
    -- Processing Status
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    chunk_count INTEGER DEFAULT 0,
    job_id VARCHAR(100) NOT NULL,
    
    -- Domain Metadata (Finance)
    company_name VARCHAR(255),
    report_type VARCHAR(50),
    financial_period VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_rag_documents_workspace_id ON b2c_finance_trader.rag_documents(workspace_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_content_hash ON b2c_finance_trader.rag_documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_rag_documents_job_id ON b2c_finance_trader.rag_documents(job_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_uploaded_by ON b2c_finance_trader.rag_documents(uploaded_by);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_rag_documents_modtime ON b2c_finance_trader.rag_documents;
CREATE TRIGGER update_rag_documents_modtime
    BEFORE UPDATE ON b2c_finance_trader.rag_documents
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();
