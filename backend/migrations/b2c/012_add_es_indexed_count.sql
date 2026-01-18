-- Add es_indexed_count column to rag_documents
ALTER TABLE b2c_finance_trader.rag_documents ADD COLUMN IF NOT EXISTS es_indexed_count INTEGER DEFAULT 0;
