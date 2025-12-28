# Search Result Formatting Issue: Table Structure & Readability

## 1. Issue Description
**Problem**: Search results containing financial tables (e.g., Profit & Loss, Balance Sheets) are displayed as raw, unformatted text or broken Markdown. This makes critical numerical data alignment lost and unreadable.

**Examples**:
- Columns run into each other (e.g., `Revenue 100 200` vs `Revenue | 100 | 200`).
- Users cannot easily distinguish between headers, line items, and values.

**Root Cause**:
- **Flattening**: Tables get flattened to text strings during PDF extraction.
- **Semantic Loss**: Embeddings treat tabular data like prose, losing row/column relationships.
- **Hallucination**: LLMs often try to "reconstruct" table structure, leading to errors.

---

## 2. Proposed Solutions

### Option A: Client-Side Markdown Rendering
*Parse and render the existing text chunks on the client.*
1.  **Markdown Component**: Use a library like `react-markdown` to render pipe tables.
2.  **Pros**: Low backend effort.
3.  **Cons**: Reliance on imperfect PDF-to-Markdown conversion; complex tables often break.

### Option B: HTML Pre-rendering
*Store tables as HTML strings.*
1.  **Store HTML**: Convert tables to `<table>` strings during ingestion.
2.  **Pros**: Preserves exact layout.
3.  **Cons**: Security risk (`dangerouslySetInnerHTML`); hard to style responsively.

### Option C: Dual Representation (User Proposal)
*Decouple storage for embedding vs. rendering.*

**Core Concept**: Do not embed raw tables. Use a **Dual Representation** strategy.

**Implementation Steps**:
1.  **Step 1: Table-Aware Ingestion**
    - Detect tables and store them in two formats:
        - **Representation A (Storage)**: Raw structured format (JSON/CSV) in a specialized store (e.g., PostgreSQL/DuckDB).
        - **Representation B (Embedding)**: A generated **Natural Language Summary** (e.g., *"Q3 2024 revenue by segment shows Cloud at $2.1B (+18% YoY)..."*).
    - **Embed ONLY the summary**.
2.  **Step 2: Hybrid Retrieval**
    - Retrieve the semantic summary via vector search.
    - If the result references a `table_id`, fetch the structured JSON/CSV.
3.  **Step 3: Explicit Rendering**
    - Frontend receives the JSON structure and renders a native, responsive Data Grid.
    - **Never** rely on LLM to reformat the table.

---

## 3. Comparative Analysis

| Solution | Robustness | Searchability | Implementation Cost |
| :--- | :--- | :--- | :--- |
| **A. Markdown Rendering** | Low (Brittle) | Medium (Raw text) | Low |
| **B. HTML Storage** | Medium | Medium | Medium |
| **C. Dual Representation** | **High** (Native JSON) | **High** (Semantic Summary) | High (New storage + Pipeline changes) |

## 4. Technical Feasibility: Extraction Engine Options

| Feature | pdfplumber (Current) | LlamaParse (Cloud) | Docling (Open Source) | PyMuPDF4LLM |
| :--- | :--- | :--- | :--- | :--- |
| **Mechanism** | Heuristic (lines/text). | Vision Model (Cloud). | Vision + Layout Models (Local). | Enhanced Rule-based. |
| **Table Accuracy** | 🔴 Low (Fails on borderless). | 🟢 High (SOTA). | 🟢 High (Specialized for charts/tables). | 🟡 Medium. |
| **Cost** | Free. | Paid (Usage based). | Free (MIT License). | Free (AGPL License). |
| **Latency** | Fast (<1s). | Slow (API call). | Medium (Local Inference). | Fast. |
| **Edge Case** | Fails on multi-column. | Robust. | Robust. | Good. |

### Analysis of New Candidates
1.  **Docling (IBM)**: 
    -   *Pros*: MIT License, specifically designed for document conversion (PDF -> Markdown/JSON), handles complex layouts/tables using vision models locally.
    -   *Cons*: Heavier dependency (requires PyTorch/Model weights).
2.  **PyMuPDF4LLM**:
    -   *Pros*: Extremely fast, lightweight.
    -   *Cons*: **AGPL License** (Viral license, risky for Enterprise software), heuristics might still struggle with very complex charts.

## 6. Recommendation
**Pivot to Docling (Option C + Docling)**.
-   **Why**: It offers the robustness of LlamaParse (vision-based layout analysis) without the cloud cost/data privacy issues. It is MIT licensed, avoiding the AGPL risks of PyMuPDF.
-   **Trade-off**: Increases container image size (needs ML libraries), but we already use `sentence-transformers`, so the delta is manageable.

**Plan**:
1.  Add `docling` to `requirements.txt`.
2.  Update `NSEEarningsParser` to use `docling.document_converter`.
3.  Use Docling's native export to Markdown/JSON directly.
