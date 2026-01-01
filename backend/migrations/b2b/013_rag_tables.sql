-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create b2b_nse schema
CREATE SCHEMA IF NOT EXISTS b2b_nse;

-- Embedding Cache (Content-Addressable "Forever" Store)
-- Helps avoid re-embedding costs on DB resets
CREATE TABLE IF NOT EXISTS b2b_nse.embedding_cache (
    content_hash VARCHAR(64) PRIMARY KEY,
    embedding vector(384), -- size for BAAI/bge-small-en-v1.5 or all-MiniLM-L6-v2
    model_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RAG Document Metadata (actual chunks go to Elasticsearch)
CREATE TABLE IF NOT EXISTS b2b_nse.rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_url TEXT NOT NULL, -- minio://bucket/path
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    
    -- Document Metadata
    company_name VARCHAR(200),
    report_type VARCHAR(50), -- 'quarterly', 'annual'
    financial_period VARCHAR(50), -- 'Q1 FY24', etc.
    
    -- Processing Status
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, ready, failed
    chunk_count INT DEFAULT 0,
    es_indexed_count INT DEFAULT 0,
    error_message TEXT,
    
    uploaded_by UUID REFERENCES b2b.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_rag_documents_tenant ON b2b_nse.rag_documents(tenant_id);
CREATE INDEX idx_rag_documents_status ON b2b_nse.rag_documents(status);

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

-- 1. Enable RLS
ALTER TABLE b2b_nse.rag_documents ENABLE ROW LEVEL SECURITY;
-- embedding_cache is SHARED/GLOBAL (content-addressable), so NO RLS (or exposed to all)
-- It contains no PII, just public vectors.

-- 2. Define Policies for rag_documents
DROP POLICY IF EXISTS rag_documents_isolation_policy ON b2b_nse.rag_documents;
CREATE POLICY rag_documents_isolation_policy ON b2b_nse.rag_documents
    USING (
        current_setting('app.is_platform_admin', true) = 'true'
        OR
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );
