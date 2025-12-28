# RAG Code Simplification Analysis

> **Objective**: Analyze current custom RAG implementation against LlamaIndex native features to identify simplification opportunities.

---

## 1. Query Decomposition vs `VectorIndexAutoRetriever`

### Current Implementation (`rag_service.py`)
*   **Code**: `_decompose_query` method (Lines 38-100).
*   **Logic**: Manually calls `AsyncOpenAI` with a custom prompt to extract `ticker`, `fiscal_year`, etc., then manually constructs `MetadataFilters`.
*   **Lines of Code**: ~60 lines.
*   **Maintenance**: High. We maintain the prompt, JSON parsing, Pydantic validation, and error handling.

### LlamaIndex Alternative: `VectorIndexAutoRetriever`
*   **Feature**: Accepts a `VectorStoreInfo` (schema definition) and an LLM. Automatically generates the prompt to infer filters from the query.
*   **Analysis**:
    *   **Pros**: Deletes the entire `_decompose_query` method. Standardizes metadata schema definition.
    *   **Cons**: Less control over the specific prompt wording (e.g., "Reliance -> RELIANCE" mapping might need fine-tuning via `prompt_template` override).
    *   **Complexity Reduction**: **High**. Replaces ~60 lines with ~5 lines of configuration.

---

## 2. Hybrid Retrieval vs `QueryFusionRetriever`

### Current Implementation (`hybrid_retriever.py`)
*   **Code**: Custom `TenantAwareHybridRetriever` class.
*   **Logic**: Manually performs: 1. Vector Search, 2. Keyword Search (ES DSL), 3. RRF Fusion (math logic), 4. Tenant Filter injection.
*   **Lines of Code**: ~150 lines (estimated).
*   **Maintenance**: High. Custom Elasticsearch JSON queries are prone to breaking on schema changes.

### LlamaIndex Alternative: `QueryFusionRetriever`
*   **Feature**: built-in class that takes a list of retrievers (Vector + Keyword) and a fusion mode (`RECIPROCAL_RANK`).
*   **Analysis**:
    *   **Pros**: Standardized RRF implementation. Easy to add more retrievers (e.g., BM25Retriever).
    *   **Cons**: Need to ensure `Tenant` filtering is correctly propagated to the underlying retrievers (might still need a thin wrapper or `filters` argument).
    *   **Complexity Reduction**: **Medium-High**. Replaces complex math/fusion logic with a standard class.

---

## 3. Response Synthesis vs `ResponseSynthesizer`

### Current Implementation (`routers/rag.py`)
*   **Code**: `search` endpoint synthesis logic.
*   **Logic**: Manually constructs `context_str` loop, defines a prompt string, calls `llm.acomplete`.
*   **Lines of Code**: ~30-40 lines.
*   **Maintenance**: Medium. String concatenation is brittle for context limits.

### LlamaIndex Alternative: `get_response_synthesizer`
*   **Feature**: Handles context stuffing, prompt formatting, and interaction with LLM. Supports `compact` (stuffing) or `tree_summarize` (recursive).
*   **Analysis**:
    *   **Pros**: Automatically handles context window overflow (truncation). Support for advanced modes like "Refine".
    *   **Cons**: Customizing the prompt text requires passing a `TextQAPrompt` object instead of a simple string.
    *   **Complexity Reduction**: **Medium**. Improves robustness (token limits) more than line count.

---

## 4. Ingestion Parsing vs `SemanticSplitterNodeParser`

### Current Implementation (`nse_parser.py`)
*   **Code**: Custom Regex-based chunking (implied/planned).
*   **Logic**: Splitting by text size or headers.

### LlamaIndex Alternative: `SemanticSplitterNodeParser`
*   **Feature**: Splits based on embedding similarity change.
*   **Analysis**:
    *   **Pros**: Keeps "The CEO's answer" in one chunk even if it's long. Better context preservation.
    *   **Cons**: Slower ingestion (requires embedding calculations during split).
    *   **Complexity Reduction**: **Low (Logic Swap)** but **High (Quality Gain)**.

---

## 5. Solving Roadmap Challenges with LlamaIndex

The following roadmap pain points can be solved using standard LlamaIndex components without custom engineering:

### A. The "Formatting & Quality" Pain (Tables)
*   **Problem**: Unreadable tables, lack of formatting.
*   **Solution**: **`LlamaParse`**.
    *   **Mechanism**: A Vision-based parser that outputs native Markdown tables.
    *   **Benefit**: Eliminates the need for custom table reconstruction logic strings.

### B. Intent-Aware Retrieval (Phase 2)
*   **Problem**: Confusing "Competitors" with "Subsidiaries".
*   **Solution**: **`RouterQueryEngine`**.
    *   **Mechanism**: Uses an LLM selector to choose between a "Competitor Filtered Tool" and a "General Tool".
    *   **Benefit**: Zero custom classification code. Just define two `QueryEngineTools`.

### C. Conversational State (Phase 3)
*   **Problem**: "What about Q3?" requires tracking previous questions.
*   **Solution**: **`CondenseQuestionChatEngine`**.
    *   **Mechanism**: Rewrites the user's latest question using the chat history context *before* retrieval.
    *   **Benefit**: Handles the "State Machine" logic automatically.

---

## Recommendation

| Component | Action | Value |
| :--- | :--- | :--- |
| **Query Decomposer** | **Replace** with `VectorIndexAutoRetriever` | High code deletion. |
| **Hybrid Retrieval** | **Keep for now** | `TenantAware` logic is unique and critical. Porting to `QueryFusion` might obscure security logic. |
| **Synthesis** | **Replace** with `ResponseSynthesizer` | Better token handling. |
| **Parsing** | **Adopt** `SemanticSplitter` | Better retrieval quality (Phase 2). |
| **Formatting** | **Adopt** `LlamaParse` | Fixes table rendering issues. |

**Conclusion**: We can significantly simplify `rag_service.py` and `routers/rag.py`. `HybridRetriever` should remain custom for security (Tenancy) unless we carefully configure LlamaIndex retrievers.
