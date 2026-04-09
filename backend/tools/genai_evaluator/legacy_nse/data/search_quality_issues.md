# Search Quality Issue: Competitors vs. Subsidiaries

## 1. Issue Description
**Problem**: When a user searches for "competitors" (e.g., "HDFC competitors"), the system retrieves and returns information about the company's **subsidiaries** (e.g., HDFC ERGO, HDFC Securities) instead of external market rivals.

**Root Cause**:
- **Semantic Ambiguity**: The current embedding model (`text-embedding-3-small`) and Retrieval method (Hybrid) struggle to distinguish the semantic nuance between "Group Companies/Subsidiaries" and "Competitors". Both concepts often appear in similar "market player" contexts.
- **Keyword Overlap**: BM25 keyword search boosts documents containing the company name ("HDFC") and generic business terms, which often strongly favoring the Annual Report sections listing subsidiaries.

---

## 2. Proposed Solutions

### Option A: Query Refinement (Negative Filtering)
*Simple heuristic improvements to the input query.*
1.  **Negative Filtering**: Explicitly exclude chunks containing terms like "subsidiary", "group company", "associate" when the query contains "competitor".
2.  **HyDE**: Use an LLM to generate a hypothetical answer listing *actual* competitors, then use that for retrieval.

### Option B: Representation Learning (Fine-tuning)
*Teaching the model to understand the financial domain relations.*
1.  **Fine-tuned Embeddings**: Train the embedding model on a financial domain dataset where "competitor" and "subsidiary" relations are explicitly labeled.

### Option C: Intent-Aware Retrieval Governance (User Proposal)
*Deterministic constraints based on query classification.*

**Core Concept**: This is not just an embedding issue but a retrieval governance issue. "Competitor" and "subsidiary" are distributionally close but business-distinct.

**Implementation Steps**:
1.  **Step 1: Query Intent Classification (Pre-Retrieval)**
    - Use a lightweight LLM to classify query into intents: `competitor_analysis`, `subsidiary_performance`, `financial_performance`.
    - Extract entities: `{"intent": "competitor_analysis", "entity": "HDFC"}`.
2.  **Step 2: Retrieval Constraints**
    - Apply strict metadata filters based on intent.
    - `IF intent == competitor_analysis THEN filter.entity_type == "competitor"`.
    - Exclude `subsidiary`, `business_unit`.
    - Enforce `exclude_company_id == HDFC_ID`.
3.  **Step 3: Explicit Grounding Guardrail (Post-Retrieval)**
    - If no results satisfy constraints, return "Not disclosed" rather than approximating.
    - **Verifier**: Reject results if `retrieved_entity.parent_id == queried_entity.id`.

---

## 3. Comparative Analysis & Brainstorming

| Solution | Pros | Cons | Metrics |
| :--- | :--- | :--- | :--- |
| **A. Negative Filtering** | • Low implementation cost<br>• Zero latency overhead | • **Brittle**: Might exclude valid sentences ("HDFC's subsidiary X competes with Y")<br>• Regex hell | • **Rejection Rate**: % of subsidiary chunks filtered. |
| **B. Fine-tuning Embeddings** | • Native semantic understanding<br>• No rigorous schema changes needed | • **High Effort**: Requires curated dataset<br>• **Drift**: Model might lose general knowledge<br>• Black box debugging | • **Cluster Distance**: Euclidean distance between "Competitor" and "Subsidiary" clusters. |
| **C. Intent-Aware Governance** | • **Deterministic Results**: High precision<br>• **Explainable**: "Filtered because metadata=subsidiary"<br>• **Safe**: Prevents hallucinations | • **Latency**: Extra LLM call (Intent)<br>• **Data Engineering**: Requires accurate `entity_type` tagging during ingestion | • **Intent Accuracy**: % of queries correctly classified.<br>• **Guardrail Trigger Rate**: How often the verifier blocks bad results. |

## 4. Verification Approach (Golden Dataset)

To validate the chosen solution, we will add the following test cases to the Golden Dataset:

1.  **Direct Competitor Query**: "Who are HDFC's main rivals?" -> *Must NOT return HDFC Bank or HDFC Life.*
2.  **Subsidiary Query**: "List HDFC subsidiaries." -> *Must return HDFC Ergo, HDFC Credila.*
3.  **Cross-Relation Query**: "Does HDFC Ergo compete with SBI General?" -> *Must handle mixed intent correctly.*

## 5. Recommendation
**Adopt Option C (Intent-Aware Governance)** as the primary strategy for Phase 2.
- **Why**: Financial data requires precision. Probabilistic methods (Embeddings) are too risky for defining corporate structure. Deterministic metadata filters (Option C) provide the necessary safety guarantees.
