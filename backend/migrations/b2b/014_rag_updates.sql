-- Add job_id and content_hash to rag_documents
ALTER TABLE b2b_nse.rag_documents 
ADD COLUMN IF NOT EXISTS job_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);

-- Index for upsert checks
CREATE INDEX IF NOT EXISTS idx_rag_documents_content_hash ON b2b_nse.rag_documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_rag_documents_job_id ON b2b_nse.rag_documents(job_id);
