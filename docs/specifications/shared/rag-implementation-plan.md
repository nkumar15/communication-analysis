# Cost-Effective RAG Implementation Plan for B2B

## Executive Summary

Implementation plan for B2B RAG with **concrete domain focus** and **validation-driven development**:
- **Phase 1 Domain**: NSE (National Stock Exchange India) **Quarterly Earnings Reports** & **Earnings Call Transcripts**
- **Architecture**: Elasticsearch + PostgreSQL
- **Strategy**: Test-driven with quality metrics at each milestone
- **Migration**: Cloud-ready (Google Vertex AI, AWS Bedrock, Azure AI)

---

## Critical Strategy: Persistence & Evaluation

### 1. Embedding Persistence (Surviving DB Resets)

**The Problem**: During development, we frequently run `make reset-db`, which wipes PostgreSQL. If we re-ingest documents, we normally lose the link to existing embeddings (or re-incur costs/time to generate them) and tenant IDs change.

**The Solution Profile**:
1.  **File-Based Seeding Config**: Read/Write tenant details to a local JSON file.
2.  **Content-Addressable Cache**: Store embeddings keyed by content hash.
3.  **Persistent Vector Store**: Keep Elasticsearch data alive.

#### A. File-Based Seeding (Config-Driven)
We will modify `backend/scripts/b2b/tenant_onboard.py` to support a **Seed Config File** (`seed_tenant_config.json`).
-   **Stable ID**: Script checks config -> uses existing `tenant_id` -> Upserts tenant.
-   **Auth Ready**: Automatically re-apply OIDC/SSO configuration.
-   **Result**: RAG embeddings stay linked; Login works instantly after reset.

#### B. Content-Hash Embedding Cache (The "Forever" Store)
We successfully avoid valid cost/time of re-embedding by caching vectors based on the **text content**.
-   **Algorithm**: `hash = sha256(chunk_text + model_name)`
-   **Result**: Re-ingesting standard NSE documents takes seconds and $0 costs.

---

### 2. Evaluation Framework (Ground Truth & Metrics)

We will use **DeepEval** (open-source) + **Synthetic Data** for unit-testing.

#### A. Metrics
-   **Context Precision**: Relevant chunks at top (> 0.8)
-   **Faithfulness**: No hallucinations (> 0.9)

#### B. Ground Truth Generation
-   **Source**: NSE Earnings Reports & Transcripts.
-   **Method**: LLM generates Q&A pairs from chunks.
-   **Review**: Human review creates Golden Dataset.

---

## Phase 1: Foundation - NSE Earnings Domain (Week 1-3)

### Domain & Objective

**Target Documents**:
1.  **Earnings Reports** (PDF): Structured Balance Sheets, P&L, Segment Revenue.
2.  **Earnings Call Transcripts** (PDF/Text): Unstructured Q&A between Management & Analysts.

**Size**: ~5 companies × (1 Report + 1 Transcript) = ~10 docs, ~300 pages.

### Parser Strategy: `NSEEarningsParser`

We will implement a specialized **`NSEEarningsParser`** that routes content to sub-parsers based on document type/section.

| Content Type | Source Document | Parsing Strategy | Chunking |
| :--- | :--- | :--- | :--- |
| **Financial Tables** | Earnings Report | **Table Extraction** (keep intact) | Whole Table + Header Context |
| **Management Speech** | Transcript | **Semantic Splitting** | 512 chars (Sentence boundary) |
| **Q&A Session** | Transcript | **Dialogue Segmentation** | Group by Speaker (Analyst + Answer) |
| **Notes/disclaimers** | Both | **Filter/Ignore** | Remove noise |

### Architecture: Elasticsearch + PostgreSQL

```
┌─────────────────────────────────────────┐
│         Application (FastAPI)           │
└──────────┬────────────────┬─────────────┘
           │                │
  Metadata │                │ Search + Vectors
           ↓                ↓
┌─────────────────┐  ┌──────────────────┐
│   PostgreSQL    │  │  Elasticsearch   │
│                 │  │                  │
│ - documents     │  │ - chunks index   │
│ - embedding_cache│ │   ├ content      │
│                 │  │   ├ embedding    │
│                 │  │   ├ metadata     │
└─────────────────┘  └──────────────────┘
```

**Elasticsearch Config**:
-   **Hybrid Search**: BM25 (Exact numbers/tickers) + kNN (Semantic context).
-   **Metadata**: `company_ticker`, `fiscal_period` (Q1FY24), `doc_type` (report/call).

### LlamaIndex Integration Strategy

**Custom Parser Implementation**:

```python
class NSEEarningsParser(NodeParser):
    def get_nodes_from_documents(self, documents):
        nodes = []
        for doc in documents:
            if self._is_transcript(doc):
                # Use Dialogue Segmenter (Speaker Diarization heuristic)
                nodes.extend(self._parse_transcript(doc))
            else:
                # Use Table Extractor + Text Splitter
                nodes.extend(self._parse_report(doc))
        return nodes
```

---

## Phase 2: Implementation Steps

### Week 1: Foundation & Persistence
1.  **Infrastructure**: Elasticsearch container + Postgres `embedding_cache` table.
2.  **Seeding**: Implement `seed_tenant_config.json` logic in `tenant_onboard.py`.
3.  **Ingestion**: Setup Basic Pipeline (Upload -> Parse -> Cache -> Index).

### Week 2: `NSEEarningsParser` Development
1.  **Table Logic**: Implement table extraction for PDFs.
2.  **Transcript Logic**: Implement speaker-based segmentation (Management/Analyst separation).
3.  **Validation**: Test `NSEEarningsParser` on Reliance/TCS Q2 documents.

### Week 3: Search & Evaluation
1.  **Hybrid Search**: Deploy Elasticsearch query DSL.
2.  **Eval**: Run DeepEval against Golden Dataset (Synthetic Q&A).

---

## Updated Technology Stack

### Phase 1 Dependencies
```
# Core RAG
llama-index-core==0.10.0
llama-index-embeddings-huggingface==0.1.4

# Evaluation
deepeval==0.20.0

# Document Processing
pypdf2==3.0.1
pdfplumber==0.10.3  # Critical for Table Extraction
tabulate==0.9.0

# Vector Store
elasticsearch==8.11.0

# Database
psycopg2-binary==2.9.9
```

### Database Schema (PostgreSQL)

**New Table: Embedding Cache**
```sql
CREATE TABLE b2b.embedding_cache (
    content_hash VARCHAR(64) PRIMARY KEY,  -- SHA256(content + model)
    embedding vector(384),
    model_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
