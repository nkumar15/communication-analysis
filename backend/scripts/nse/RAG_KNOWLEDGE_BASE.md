# NSE Domain RAG Knowledge Base

> **Single Source of Truth** for the NSE Earnings Analysis RAG System.
> *Last Updated: December 2025*

---

## 1. System Architecture (The "Solution")

Our RAG system is designed to handle complex financial queries with high precision (>87% Faithfulness). It moves beyond naive vector search to a multi-stage pipeline.

### 1.1 The Pipeline (Hybrid + Rerank + Ground)

1.  **Retrieval (Hybrid)**:
    *   **Vector Search**: Finds semantic matches (concepts).
    *   **Keyword Search (BM25)**: Finds exact matches (tickers, specific metrics like "EBITDA").
    *   **Fusion**: Reciprocal Rank Fusion (RRF) combines these into `top_k=20` candidates.
2.  **Reranking (Precision)**:
    *   **Model**: `CrossEncoder` (`ms-marco-MiniLM-L-6-v2`).
    *   **Logic**: Re-scores the 20 candidates by reading the Query + Document pair together.
    *   **Normalization**: Raw logits are passed through a Sigmoid function to get 0-1 probabilities.
    *   **Filtering**: **Hard Threshold (0.25)**. Any chunk with < 25% relevance is discarded.
3.  **Generation (Faithfulness)**:
    *   **Model**: `gpt-4o-mini`.
    *   **Strategy**: "Grounding Prompt".
    *   **Prompt Logic**: "Extract exact quotes first. If no quotes support the answer, say 'I don't know'."

### 1.2 "Hard Negative" Defense (Competitors vs. Subsidiaries)
**Problem**: Naive vector search confuses "HDFC Competitors" with "HDFC Subsidiaries" (both appear in similar contexts).
**Solution**:
1.  **Reranker**: Assigns low scores to "Subsidiary" chunks when the query asks for "Competitors". The 0.25 threshold filters them out.
2.  **Strict Prompt**: If a subsidiary chunk sneaks through, the LLM is forbidden from hallucinating. It checks the text, sees it implies "ownership" not "rivalry", and refuses to cite it.

### 1.3 Table Formatting (Dual Representation)
**Problem**: Financial tables (P&L) get mangled into unreadable text.
**Solution**:
*   **Dual Representation**: We extract tables and store them as **Structure** (JSON) for rendering but **Generate Summaries** (Text) for embedding.
*   **Frontend**: The UI detects table-like data and renders a structured grid/markdown table rather than raw text blocks.

### 1.4 Known Issue: Cross-Entity Hallucination
**Problem**: Queries like "Employee benefit expenses TCS" return tabular data for "Infosys".
**Root Cause**:
1.  **Semantic Dominance**: The embedding for "Employee benefit expenses" is identical across companies.
2.  **Entity Blindness**: The vector model captures the "finance concept" efficiently but treats the entity name ("TCS") as just another keyword, which is outweighed by the dense financial match in the competitor's document.
**Proposed Solution (Phase 2)**:
*   **Metadata Filtering**: Extract `company_name` (e.g., "TCS") during ingestion and store as metadata.
*   **Query Routing**: Parse the user query to extract entities (`filters: {company: "TCS"}`) and apply a Hard Filter on the vector search.

---

## 2. Experimentation Strategy

We do not guess; we measure.

### 2.1 Golden Dataset
*   **Source of Truth**: `backend/scripts/nse/data/dataset/`
*   **Composition**:
    *   80% Synthetic (Generated from docs).
    *   10% Hand-Crafted (Real hard queries).
    *   10% **Hard Negatives** (Queries with NO answer in docs).
*   **Metric**: We optimize for **Faithfulness** (Safety) and **Context Recall** (Coverage).

### 2.2 Re-Embedding (Blue-Green Indexing)
When upgrading embedding models:
1.  Create new index `rag_nse_v2`.
2.  Backfill data.
3.  Compare metrics.
4.  Switch alias `rag_nse` -> `rag_nse_v2`.

---

## 3. Future Roadmap

### Phase 3: Conversational Intelligence (State Awareness)
*   **Problem**: "What is the latest revenue?" (System lacks concept of "latest" or "last query").
*   **Solution**: **Query State Machine**.
    *   Track `(Company, Period, Metric)` in a session object.
    *   Resolve "How about Q3?" -> `Period=Q3` + `Metric=[Previous Metric]`.

### Phase 4: Multi-Domain Scaling
*   **Goal**: Expand to "Enron Emails" and "SEC Filings".
*   **Action**: Modularize `RagService` (Done) and create domain-specific Parsers/Rerankers.

---

## 4. Troubleshooting & Operational Runbook

*   **"Error Generating Answer"**: Usually missing specific LLM dependency (`llama-index-llms-openai`) in the API container.
*   **Relevance Drop**: Check `RerankerFactory`. Ensure model is cached and not downloading on every request.
*   **Hallucinations**: Verify the Prompt Strategy in `rag.py`. It MUST include "Extract quotes".

---

## 5. Artifact Index
*   **Experiment Logs**: [`EXPERIMENT_REGISTRY.md`](./data/EXPERIMENT_REGISTRY.md) (The active log of all runs).
*   **Evaluation Script**: `evaluate_rag.py`.

---

## 6. Taxonomy of Financial RAG Failures

A catalog of known and potential failure modes specific to Earnings Calls & Financial Reports.

| Category | Description | Example Scenario | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **1. Entity Ambiguity (Cross-Tenant)** | Vector search retrieves documents from the wrong company due to generic financial terminology. | Query: *"TCS Margins"* <br>Result: *"Infosys Margins"* (because "Margins" vector is strong). | **Metadata Filtering**: Hard filter by `ticker` or `company_name`. |
| **2. Structural Loss (Tabular)** | Parsing tools flatten complex tables into unstructured text, losing row/column alignment. | Query: *"Q2 FY25 Revenue"* <br>Result: Returns revenue for "Q2 FY24" because alignment was lost. | **Vision/Layout Models**: Use Azure Layout to preserve grid structure (JSON). |
| **3. Temporal Ambiguity** | LLM/Retriever fails to distinguish between quarters or fiscal years. | Query: *"Latest revenue"* <br>Result: Returns FY23 data because it had higher keyword density. | **Recency Weighting**: Boost newer documents in retrieval. <br>**Metadata**: Explicit `fiscal_year` filtering. |
| **4. Scope Ambiguity** | Confusion between "Standalone" and "Consolidated" figures. | Query: *"Net Profit"* <br>Result: Extracts Standalone profit (lower) instead of Consolidated (higher). | **Chunk Enrichment**: Prepend "Scope: Consolidated" to chunk text during ingestion. |
| **5. Hard Negatives (Relational)** | Semantic similarity captures related entities (Subsidiaries, Partners) instead of the requested relation (Competitors). | Query: *"Competitors"* <br>Result: *"We invested in Subsidiary X..."* | **Reranking**: Cross-Encoder to filter non-relevant relationships. <br>**Strict Prompting**. |
| **6. Unit Hallucination** | misinterpretation of financial units (Crores, Lakhs, Millions, USD). | Query: *"Revenue in USD"* <br>Result: Treats INR Crores as USD. | **Standardization**: Normalize all matching fields to a base currency in metadata? <br>**Prompt**: "Always cite original units". |
| **7. Speaker Attribution** | In Concalls, confusing Management statements with Analyst questions. | Query: *"Guidance for FY26"* <br>Result: Cites an Analyst *asking* about guidance, not the answer. | **Diarization**: Tag chunks with `speaker_role: "Management"` or `"Analyst"`. |
| **8. Forward-Looking vs Actuals** | Confusing official Guidance/Outlook with actual historical results. | Query: *"Q4 Results"* <br>Result: Returns the *Outlook* for Q4 from the Q3 call. | **Section Classification**: Classify chunks as "Outlook" vs "Financials". |

---

## 7. Prioritized Implementation Roadmap (Cost-Optimized)

> **Detailed Design**: See [`AZURE_PARSING_STRATEGY.md`](./AZURE_PARSING_STRATEGY.md) for the technical specification of the "Golden Cache" and Semantic Chunking logic.

To address the failure modes above without ballooning Azure/OpenAI costs, we will follow this **"Parse Once, Enrich Offline"** strategy.

### Stage 1: The "Golden Cache" (Immediate Priority)
**Goal**: Never call Azure Document Intelligence twice for the same PDF.
*   **Action**: Update `AzureParsingStrategy` to save the **Raw Azure JSON Response** to disk (e.g., `.processed/<content_hash>.json`).
*   **Benefit**: We can iterate on Table Formatting, Chunking strategies, and Metadata extraction infinitely using the cached JSON. Zero marginal cost.
*   **Solves**: Budget constraints during development.

### Stage 2: Metadata Enrichment (One-Pass)
**Goal**: Solve Entity, Temporal, and Scope ambiguities in one go.
*   **Action**: Before chunking, send the **First Page Text** (from Cache) to `gpt-4o-mini` to extract a "Global Metadata" object:
    ```json
    {
      "ticker": "TCS",
      "fiscal_year": "2025",
      "period": "Q2",
      "currency": "INR",
      "scope": ["Consolidated", "Standalone"]
    }
    ```
*   **Apply**: Stamp this metadata onto *every chunk* generated from the document.
*   **Solves**:
    *   **Entity Ambiguity** (Filter by `ticker=TCS`)
    *   **Temporal Ambiguity** (Filter by `fiscal_year=2025`)
    *   **Unit Hallucination** (Context includes `currency=INR`)

### Stage 3: Structural & Section Tagging (Offline)
**Goal**: Use Azure's layout data to classify chunks (without new API calls).
*   **Action**: Use the cached Azure Layout (Headers/Paragraphs) to detect:
    *   **"Speaker"**: Text following "Operator:" or "Mr. Chandrasekaran:" -> Tag as `speaker_role`.
    *   **"Section"**: Text under header "Outlook" -> Tag as `section_type: outlook`.
*   **Solves**:
    *   **Speaker Attribution**
    *   **Forward-Looking Hallucinations**

---

## 8. Advanced Capabilities Roadmap (Future)

### 8.1 Intent-Aware Retrieval (Phase 2)
*Goal: Eliminate "Silent Failures" (Semantic Drift)*
- **Objective**: Stop returning Subsidiaries when asked for Competitors.
- **Action**:
    - **Classifier**: Implement lightweight LLM call to classify intent (`competitor`, `financials`, `general`).
    - **Filters**: Enforce metadata constraints (e.g., `exclude_type=subsidiary`).
- **Outcome**: Search results are semantically accurate, not just vector-similar.

### 8.2 Conversational Intelligence (Phase 3)
*Goal: Enable natural, analyst-like workflow.*
- **Query State Machine**: Handle "latest", "last quarter", and "compare them".
    - **Backend**: Implement Session State object (`{company, period, metric}`).
    - **Logic**: State resolver updates context before retrieval.
- **Time-Aware Chunking**: Ensure retrieval respects strict fiscal periods.
    - Refine chunking to never cross document/quarter boundaries.
    - Strict `fiscal_period` tagging.
