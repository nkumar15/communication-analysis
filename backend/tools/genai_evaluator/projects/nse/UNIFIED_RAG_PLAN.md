# Unified RAG Analysis Implementation Plan

## Objective
Transition from "Single-Document QA" to **"Unified Multi-Hop Analysis"** where the RAG system synthesizes insights from both **Earnings Reports** (Quantitative Data) and **Conference Call Transcripts** (Qualitative Context).

---

## 1. Updates to Experiment Framework

### 1.1 Dataset Generation Module (New)
*   **Current State**: Legacy script (`legacy_nse/generate_dataset.py`) is single-file only.
*   **New Component**: `backend/scripts/evaluation/core/dataset_generator.py`
*   **Logic**:
    1.  **Paired Loading**: Iterate over `source_documents/` and group files by `ticker` + `quarter`.
        *   Example Group: `TCS_Q2_FY26` -> [`tcs_earnings.pdf`, `tcs_concall.pdf`]
    2.  **Cross-Context Prompting**:
        *   *Input*: Earnings Table (Revenue) + Concall Text (CEO Statement).
        *   *Prompt*: "Create a question asking to explain the Revenue figure using the CEO's statement."
    3.  **Output**: `unified_gold_dataset.json` with `source_types=["earnings", "concall"]` metadata.

### 1.2 Evaluation Metrics
*   **New Metric**: `SourceAttributionMetric` (DeepEval Custom Metric).
*   **Logic**:
    *   Pass: Retrieval Context contains at least 1 chunk from `earnings` AND 1 chunk from `concall`.
    *   Fail: Retrieval is single-source only (misses the full picture).

---

## 2. Ingestion Pipeline Updates

### 2.1 Metadata Strategy
The UI and API must support uploading "Document Sets".
*   **Backend**: `RagService` needs to accept `doc_type` explicitly.
    *   `doc_type='financial_report'` (Earnings, Balance Sheet).
    *   `doc_type='management_transcript'` (Concall, Earnings Call).
*   **Frontend**: Multi-file upload widget ("Upload Report" + "Upload Transcript").

### 2.2 chunking Strategy
*   **Financial Reports**: Continue with `Docling` (Preserve Tables).
*   **Transcripts**: Use **Speaker-Aware Chunking**.
    *   We must distinguish "Analyst Question" from "Management Answer".
    *   *Why?* We want to cite the CEO, not the Analyst asking the question.

---

## 3. Execution Roadmap

### Phase 1: Framework Upgrade (Evaluation Side)
1.  **Port Generation Logic**: Implement `core/dataset_generator.py`.
2.  **Generate Dataset**: Create `unified_gold_dataset_v1.json` using the new TCS/Infosys files.
3.  **Baseline Run**: Run current RAG against this new dataset.
    *   *Hypothesis*: It will fail (Faithfulness low) because it retrieves quantitative data but misses the "Why" (Concall).

### Phase 2: Ingestion Upgrade (Production Side)
1.  Update `RagService` to handle `doc_type`.
2.  Update `ingest_document_task` to index `doc_type` in Elasticsearch/VectorStore.

### Phase 3: "Union" Experiment
1.  Configure `experiment_unified.yaml`.
2.  Tweak Retriever: `hybrid_search` with weights suitable for both dense text (concall) and sparse numbers (earnings).
3.  Validate `SourceAttribution` score.

---

## 4. Documentation Strategy

### 4.1 Capturing in Knowledge Base
*   **New Section**: "Unified Analysis".
*   **Decision Record**: "Adopted Paired Ingestion to solve 'The Why' queries."

### 4.2 Capturing in Registry
*   **New Columns**: `Source Diversity` score.
*   **Version**: `experiment_v2_unified`.
