# RAG Enhancement Roadmap: From MVP to Financial Intelligence

## Executive Summary
This roadmap synthesizes the strategies for **Table Formatting**, **Search Quality**, and **State-Awareness** into a phased execution plan.

**Core Philosophy**:
1.  **Visibility First**: We cannot improve what users cannot read (Tables).
2.  **Precision Second**: Financial search requires strict filtering (Competitors vs Subsidiaries).
3.  **Intelligence Third**: Multi-turn and temporal context requires a solid foundation of precision.

---

## Phase 1: Foundation & Visibility (Weeks 1-2)
*Goal: Make the system usable and measurable.*

### 1.1 Experimentation Framework (Prerequisite)
- **Objective**: Establish the "Golden Dataset" to measure improvements.
- **Action**: Create `backend/scripts/nse/data/dataset/` with:
    - 50 Synthetic Q&A pairs.
    - 10 Hard Negative pairs.
    - Automated evaluation script (`deepeval`).
- **Outcome**: A baseline score (e.g., F1 Score: 0.72) to beat.

### 1.2 Table Formatting (Dual Representation)
- **Objective**: Fix unreadable financial tables.
- **Action**:
    - **Ingestion**: Update pipeline to extract tables -> Store Summary (Vector) + JSON (SQL/Mongo).
    - **Frontend**: Update `RagKnowledgeBasePage` to render JSON tables natively.
- **Outcome**: Users can read P&L statements. Eliminates the biggest UX complaint.

---

## Phase 2: Precision & Governance (Weeks 3-4)
*Goal: Eliminate "Silent Failures" (Semantic Drift).*

### 2.1 Intent-Aware Retrieval
- **Objective**: Stop returning Subsidiaries when asked for Competitors.
- **Action**:
    - **Classifier**: Implement lightweight LLM call to classify intent (`competitor`, `financials`, `general`).
    - **filters**: Enforce metadata constraints (`exclude_type=subsidiary`).
- **Outcome**: Search results are semantically accurate, not just vector-similar.

### 2.2 Blue-Green Re-Embedding
- **Objective**: Support the new metadata requirements for Phase 2.
- **Action**:
    - Create `rag_nse_v2` index.
    - Re-ingest with updated metadata tags (`entity_type`, `report_section`).
    - Switch alias.

---

## Phase 3: Conversational Intelligence (Weeks 5-6)
*Goal: Enable natural, analyst-like workflow.*

### 3.1 Query State Machine
- **Objective**: Handle "latest", "last quarter", and "compare them".
- **Action**:
    - **Backend**: Implement Session State object (`{company, period, metric}`).
    - **Logic**: State resolver updates context before retrieval.
- **Outcome**: Users can have a dialogue with the data.

### 3.2 Time-Aware Chunking
- **Objective**: Ensure retrieval respects strict fiscal periods.
- **Action**:
    - Refine chunking to never cross document/quarter boundaries.
    - Strict `fiscal_period` tagging.

---

## Summary of Priority
1.  **Experimentation** (Must measure)
2.  **Table Formatting** (Must read)
3.  **Search Quality** (Must trust)
4.  **State Awareness** (Must converse)
