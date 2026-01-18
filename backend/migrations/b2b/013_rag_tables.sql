-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create b2b_nse schema
CREATE SCHEMA IF NOT EXISTS b2c_finance_trader;

-- Embedding Cache (Content-Addressable "Forever" Store)
-- Helps avoid re-embedding costs on DB resets
CREATE TABLE IF NOT EXISTS b2c_finance_trader.embedding_cache (
    content_hash VARCHAR(64) PRIMARY KEY,
    embedding vector(384), -- size for BAAI/bge-small-en-v1.5 or all-MiniLM-L6-v2
    model_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);


