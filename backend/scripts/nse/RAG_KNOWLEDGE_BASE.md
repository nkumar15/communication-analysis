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
