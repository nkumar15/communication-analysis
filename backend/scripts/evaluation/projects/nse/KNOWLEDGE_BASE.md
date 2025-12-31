# NSE Domain RAG Knowledge Base

> **Single Source of Truth** for the NSE Earnings Analysis RAG System.
> Unifies insights from Experiments, Architecture Decisions, and Failure Analysis.

---

## 1. Key Learnings (The "Wins")

| Finding | Source Experiment | Confidence | Application |
|---------|-------------------|------------|-------------|
| **Hybrid Search dominates Vector-only** | Exp #2 (v0) | High | **Robustness**: Vectors capture concepts ("expenses") but fail on acronyms/IDs. BM25 guarantees alignment on exact keywords (e.g., Table Headers). |
| **Reranking improves precision** | Exp #13 (v1) | High | **Hard Threshhold**: Any chunk with < 25% relevance is discarded. Resolves "Rank Ties" where irrelevant keyword matches crowded out semantic matches. |
| **Grounding Prompts Reduce Hallucination** | Exp #13 (v1) | High | "Grounding CoT" prompt (Extract quotes -> Synthesize) is now the standard. Significantly reduced "I don't know" rates compared to standard prompts. |
| **Table Parsing is Critical** | Exp #1 (v0) | High | **Dual Representation**: Standard chunking mangles tables. We must extract tables as structure (JSON/Markdown) but embed them as text summaries. |
| **gpt-4o-mini is cost-effective** | Exp #4 (v1) | Medium | Replaced gpt-4 for routine synthesis with minimal quality loss (Faithfulness > 87%). |

---

## 2. Taxonomy of Financial RAG Failures

A catalog of known failure modes specific to Earnings Calls & Financial Reports.

| Category | Description | Mitigation Strategy |
| :--- | :--- | :--- |
| **1. Entity Ambiguity (Cross-Tenant)** | Vector search retrieves "Infosys Margins" when asked for "TCS Margins" due to generic financial terms. | **Metadata Filtering**: Hard filter by `ticker` or `company_name`. |
| **2. Structural Loss (Tabular)** | Parsing tools flatten complex P&L/Balance Sheets into prose, losing row/column alignment. | **Docling Integration**: Use vision-based models to preserve table structure as Markdown/JSON. |
| **3. Temporal Ambiguity** | System fails to distinguish "latest revenue" vs "previous quarter" or mixed fiscal years. | **Recency Weighting** & **State Machine**: Track `fiscal_year` in metadata and query state. |
| **4. Scope Ambiguity** | Confusion between "Standalone" and "Consolidated" figures. | **Chunk Enrichment**: Prepend "Scope: Consolidated" to chunk text during ingestion. |
| **5. Hard Negatives (Relational)** | "Competitors" query returns "Subsidiaries" because they appear in similar contexts. | **Intent-Aware Governance**: Classify intent (`competitor_analysis`) and apply negative filters (`exclude_type=subsidiary`). |
| **6. Unit Hallucination** | Misinterpretation of financial units (Crores vs Millions). | **Prompt Engineering**: "Always cite original units". |

---

## 3. Architectural & Strategic Decisions

### 3.1 Parsing: Pivot to Docling
*   **Problem**: `pdfplumber` (heuristic) fails on borderless tables. `LlamaParse` (Cloud) is too expensive/private.
*   **Decision**: Adopt **Docling (IBM)**.
*   **Why**: Open Source (MIT), runs locally, uses vision models for SOTA table extraction.
*   **Status**: Recommended (See *Legacy `search_result_formatting.md`*).

### 3.2 Entity Governance: Intent-Aware Retrieval
*   **Problem**: Semantic search cannot distinguish "Subsidiary" from "Competitor" reliably.
*   **Decision**: **Deterministic Governance**.
    1.  **Classify Intent**: LLM tags query `intent: competitor_analysis`.
    2.  **Apply Constraints**: Enforce `exclude_type: subsidiary` in Metadata Filters.
*   **Status**: Planned for Phase 2.

### 3.3 State Management: Query State Machine
*   **Problem**: "What is the revenue?" followed by "How about Q3?" fails in a stateless system.
*   **Decision**: Implement **Session State Object** `{Company, Period, Metric}`.
    *   Resolves "Q3" -> `Period="Q3 2025"`.
    *   Resolves "Latest" -> `Period=MAX(Date)`.
*   **Status**: Planned for Phase 3 (Conversational Intelligence).

---

## 4. Experiment History & Context

### Dataset v0 (Legacy)
*   **Focus**: Proof of Concept. 20 Questions.
*   **Major Milestone**: **Exp #2 (Hybrid Search)** proved that client-side RRF (Reciprocal Rank Fusion) could provide Enterprise-grade ranking without paying for Elasticsearch Platinum.

### Dataset v1 (Current)
*   **Focus**: Domain Specificity (Hard Negatives, formatted tables).
*   **Major Milestone**: **Exp #13 (Strong Model + Content)**.
    *   **Config**: `gpt-4o-mini`, `top_k=20` (Hybrid), `top_n=10` (Reranked).
    *   **Result**: Faithfulness 87.5%, Recall 93.8%.
    *   **Outcome**: Deployment Candidate.

---

## 5. Open Questions & Roadmap

- [ ] **Table Chunking**: Can we preserve Markdown tables better during chunking? (Planned Exp #8)
- [ ] **HyDE**: Will Hypothetical Document Embeddings help with vague user queries?
- [ ] **Fine-tuning**: Is it worth fine-tuning an embedding model on Indian financial terminology?
