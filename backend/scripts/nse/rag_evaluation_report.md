# RAG Evaluation Scorecard

**Objective**: Scientifically measure the improvement of our RAG pipeline as we move from Naive implementation to Advanced (Domain-Specific) architecture.

## 1. Methodology
*   **Dataset**: TCS Q2 FY26 Financial Results (Test Set - Held out from development).
*   **Tool**: `deepeval` (Unit Testing for LLMs).
*   **Ground Truth**: Synthetically generated Q&A pairs (Golden Dataset) derived from the Test Set.

## 2. Configuration Snapshot
*   **LLM Model**: `gpt-5-nano` (via OpenAI API)
*   **Embedding Model**: `text-embedding-3-small` (via OpenAI API)
*   **Vector Store**: Elasticsearch 8.11
*   **Reranker**: *None (Baseline)*

## 3. Metrics Definitions
| Metric | Definition | Good Score | What it tells us |
| :--- | :--- | :--- | :--- |
| **Faithfulness** | Does the answer hallucinate? (Answer == Context?) | > 0.9 | Trustworthiness |
| **Answer Relevancy** | Does the answer address the user's prompt? | > 0.8 | Usefulness |
| **Context Recall** | Did the retriever find the *exact* paragraph needed? | > 0.8 | Retrieval Quality |

## 4. Performance Log

| Experiment | Date | Faithfulness | Relevancy | Context Recall | LLM | Embedding |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline (Naive)** | 2025-12-26 | **100%** | **100%** | **66.7%** | gpt-5-nano | text-embedding-3-small |
| **Exp 1: Table Parser** | 2025-12-26 | **100%** | **100%** | **100%** | Fixed Recall failure via Markdown Tables |
| **Exp 2: Hybrid Search** | *Pending* | - | - | - | Linear Combination (BM25 + kNN). |
| **Exp 3: Reranking** | *Pending* | - | - | - | Cross-Encoder Reranker (ColBERT/BGE). |

## 4. Qualitative Analysis
*Section to paste specific "Win/Loss" examples.*

### Baseline Issues (Root Cause Analysis)
*   **Context Recall Failure (Score 66.7%)**:
    *   **Issue**: For the query *"How much did TCS spend on employee benefit expenses?"*, the retriever returned chunks from the **Balance Sheet** ("Employee benefit obligations") instead of the **Profit & Loss Statement** ("Employee benefit expenses").
    *   **Root Cause**: Semantic Ambiguity. The naive chunking likely separated the P&L table into a text block where "expenses" wasn't weighted heavily enough against "obligations" by the embedding model (`text-embedding-3-small` without reranker).
    *   **Impact**: The LLM correctly stated it couldn't find the answer in the provided (wrong) context.
*   **Tables**: Naive parsing flattens tables (like P&L) into unstructured text, causing loss of row/column alignment. This makes extracting specific line items relies heavily on the chunk just happening to contain the label and number in close proximity.

### Improvement Evidence
*   **Exp 1 (Table Parser)**:
    *   **Win**: Successfully answered *"How much did TCS spend on employee benefit expenses?"*.
    *   **Why**: The parser extracted the P&L table as a distinct node. The standard text chunking did not mangle the row `Employee benefit expenses | 38,606`.
    *   **Metdata**: Added `table_rows` and `table_columns` to nodes, allowing future filtering.
