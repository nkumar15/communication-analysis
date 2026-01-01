# RAG (Retrieval-Augmented Generation) Specification & Architecture

**Version:** 1.1
**Last Updated:** January 1, 2026
**Status:** Active Development
**Architecture:** Elasticsearch + PostgreSQL
**Experiment Registry:** [Experiment Registry](../../../backend/scripts/evaluation/projects/nse/EXPERIMENT_REGISTRY.md)

---

## Executive Summary

This document serves as the master specification for the Retrieval-Augmented Generation (RAG) system for our multi-tenant SaaS. It consolidates the architecture decisions, implementation plan, and experimental framework findings.

### Key Architecture Decisions
-   **Hybrid Search:** Elasticsearch (BM25 + Vector + RRF Fusion).
-   **Metadata/Storage:** PostgreSQL (Tenants, Documents, Queries) + S3/MinIO (Files).
-   **Framework:** LlamaIndex (Parsing, Node Management) + Custom Retrievers.
-   **Evaluation:** DeepEval + Synthetic Golden Datasets.

---

## 1. Experimental Development Framework

We have adopted an **Experiment-Driven Development** approach for RAG to ensure quality and cost-effectiveness.

### The Process
1.  **Hypothesis**: Define a change (e.g., "Top-K 10 is better than 5").
2.  **Experiment**: Run the change against a fixed "Golden Dataset" (e.g., NSE Earnings Reports).
3.  **Evaluate**: tailored metrics (Faithfulness, Recall) via `DeepEval`.
4.  **Register**: Log results in `EXPERIMENT_REGISTRY.md`.

### Validated Configuration (Production)
Based on **Experiment #13 (v1)**, the winning configuration is:
-   **Retrieval:** Hybrid (BM25 + Vector) with `top_k=20`.
-   **Reranking:** Cross-Encoder reranker reducing to `top_k=10`.
-   **Generation:** `gpt-4o-mini` with a **Grounding CoT (Chain of Thought) Prompt**.
-   **Performance:** Faithfulness **87.5%**, Recall **93.8%**.

---

## 2. Architecture Overview

### System Diagram

```mermaid
graph TD
    User[User] -->|Query| API[FastAPI Wrapper]
    API -->|1. Embed Query| Embed[Embedding Model]
    API -->|2. Hybrid Search| ES[Elasticsearch]
    ES -->|BM25 + Vector| ES
    ES -->|3. RRF Fusion| API
    API -->|4. Rerank| Rerank[Cross Encoder]
    API -->|5. Synthesize| LLM[LLM (gpt-4o-mini)]
    LLM -->|Response| User
    
    subgraph Data Layer
    ES
    PG[PostgreSQL Metadata]
    end
```

### Component Breakdown

#### A. Ingestion Pipeline
1.  **Upload**: Document stored in S3/MinIO.
2.  **Parse**: `LlamaParse` for PDFs (handles tables well), `SentenceSplitter` for text.
3.  **Chunk**: Semantic splitting/Fixed-size chunking.
4.  **Embed**: Generate vectors (e.g., `text-embedding-3-small`).
5.  **Index**: Store in Elasticsearch (Fields: `content`, `embedding`, `tenant_id`, `metadata`).

#### B. Retrieval Pipeline (Hybrid)
We do **not** use standard LlamaIndex retrievers because of strict **Multi-Tenancy** requirements.
-   **Vector Search**: Cosine similarity on embeddings.
-   **Keyword Search**: BM25 on text fields.
-   **Fusion**: Reciprocal Rank Fusion (RRF) with `k=60`.
-   **Tenant Isolation**: All queries **MUST** filter by `tenant_id` at the index level.

#### C. Synthesis
-   **Model**: `gpt-4o-mini` (Cost/Performance sweet spot).
-   **Prompting**: Strict "Answer based ONLY on context" instructions with citations.

---

## 3. Implementation Plan

### Phase 1: Foundation (Completed/In-Progress)
-   [x] **Infrastructure**: Elasticsearch, PostgreSQL, MinIO setup.
-   [x] **Experimental Framework**: DeepEval setup, Initial NSE dataset experiments.
-   [x] **Hybrid Search**: Custom RRF implementation.
-   [ ] **API Integration**: Connect `RagService` to the experimental winning config.

### Phase 2: Advanced Features (Q1 2026)
-   **Table Processing**: Move to `LlamaParse` for better table markdown extraction (Experiment #8).
-   **Workspace Isolation**: Extend `tenant_id` filter to `workspace_id`.
-   **Query Decomposition**: Break complex queries into sub-questions (Reference `rag_simplification.md` logic).

### Phase 3: Optimization
-   **Embedding Cache**: Hash-based caching to survive DB resets (SHA256 of content).
-   **Fine-tuning**: Fine-tune embedding model on domain specific data if recall drops.

---

## 4. Operational Maintenance

### Experiment Registry
Always check `backend/scripts/evaluation/projects/nse/EXPERIMENT_REGISTRY.md` before changing RAG parameters (`top_k`, prompts, models).

### Cost Management
-   **Dev**: Use `Ollama` (Local) or `gpt-4o-mini` (Cloud).
-   **Prod**: `gpt-4o-mini` is the default. `gpt-4` only for complex reasoning tasks.

---

## 5. Reference
-   [Hybrid Search Educational Guide](../../architecture/shared/rag-hybridsearch.md)
