# State-Aware Query & Retrieval Issue: Time, Context, & Follow-ups

## 1. Issue Description
**Problem**: The current RAG implementation is **stateless**. It treats every query as an isolated event, covering strictly vector similarity. This fails in:
1.  **Temporal Context**: "What is the *latest* revenue?" (System doesn't know "latest").
2.  **Conversational Follow-ups**: "How about in Q3?" (System doesn't know "what" about Q3).
3.  **Ambiguity**: "Compare them" (System doesn't know who "they" are).

**Root Cause**:
- **Isolated Retrieval**: No memory of previous entity/metric.
- **Distributional Overlap**: "Subsidiary" and "Competitor" vectors are close.
- **Missing State**: No explicit tracking of `(Company, Period, Metric)`.

---

## 2. Proposed Solutions

### Option A: Contextual Query Rewriting
*LLM rewrites follow-ups into standalone queries.*
- **Mechanism**: "How about Q3?" -> "What is HDFC revenue in Q3?"
- **Pros**: Easy to implement via LangChain standard chains.
- **Cons**: Adds latency; doesn't solve "latest" (requires external grounding); hallucination risk.

### Option B: Time-Aware Metadata
*Regex/NER extraction of dates to apply filters.*
- **Mechanism**: Extract "2024", "last year" -> Filter `period='2023'`.
- **Pros**: Precise filtering.
- **Cons**: Brittle for complex relative times ("same quarter pre-covid").

### Option C: Query State Machine (User Proposal - Recommended)
*Explicitly track and maintain a structured query state.*

**Core Concept**: Treat retrieval as a state machine where the context is explicitly resolved before hitting the vector store.

**Implementation Steps**:
1.  **Step 1: Maintain Explicit Query State**
    - Track a state object:
      ```json
      {
        "company": "Company A",
        "period": "Q3 2024",
        "metric": "revenue",
        "currency": "USD"
      }
      ```
    - **Follow-up Resolution**: When user asks "How about last quarter?", logic updates *only* `period` to "Q2 2024", keeping `company` and `metric`.

2.  **Step 2: Time-Aware Chunking (Ingestion)**
    - Tag every chunk with `fiscal_quarter`, `fiscal_year`, `report_type`.
    - **Avoid mixing periods** inside a single chunk.

3.  **Step 3: Retrieval Using State + Vector**
    - Construct filter: `metadata.company='Company A' AND metadata.period='Q3 2024'`.
    - Vector Query: "revenue".
    - Intent Constraints: `exclude entity_type='subsidiary'` (if studying competitors).

4.  **Step 4: Stateful Answer Synthesis**
    - Inject state into LLM prompt:
      > Current State: Company: A | Period: Q3 2024 | Metric: Revenue

---

## 3. Reference Architecture

```mermaid
graph TD
    UQ[User Query] --> IE[Intent & Entity Extractor (LLM)]
    IE --> QSR[Query State Resolver]
    QSR --> State{Update State}
    State -->|Context Updated| HR[Hybrid Retriever]
    
    subgraph Retrieval
    HR --> V[Vector DB (Narratives)]
    HR --> SQL[SQL (Tables)]
    HR --> MF[Metadata Filters]
    end
    
    HR --> GV[Grounding Verifier]
    GV --> AG[Answer Generator]
```

## 4. Comparative Analysis

| Solution | Context Retention | Temporal Accuracy | Latency | Implementation Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **A. Rewriting** | Medium | Low (LLM guess) | High (Double Gen) | Low |
| **B. Metadata** | Low | High (Strict) | Low | Medium |
| **C. State Machine** | **High** (Deterministic) | **High** (Resolved) | Medium | High (State logic) |

## 5. Advanced Enhancements
1.  **Content-Type Routing**: Separate embeddings for Narratives vs. Tables vs. Guidance. Route query based on intent.
2.  **Knowledge Graph**: Use graph to resolve "Competitor" or "Subsidiary" relationships *before* retrieval.
3.  **Evaluation Metrics**:
    - **Table Fidelity Score**: Accuracy of retrieved numbers vs ground truth.
    - **Entity Leakage Rate**: % of times a subsidiary is retrieved as a competitor.
    - **Temporal Accuracy**: % of times "latest" resolves to correct Q_MAX.

## 6. Recommendation
**Adopt Option C (Query State Machine)**.
- **Why**: Financial analysis differs from general chat because **dimensions (Time, Entity, Metric)** are strict constraints. A state machine enforces these constraints deterministically, whereas pure vector search "drifts".
