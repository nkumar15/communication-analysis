# NSE RAG Scripts & Documentation

This directory contains the experimentation scripts and knowledge base for the **NSE Earnings Analysis RAG**.

## 📖 Key Documentation

*   **[`RAG_KNOWLEDGE_BASE.md`](./RAG_KNOWLEDGE_BASE.md)**  
    Starts here. The single source of truth for:
    *   **Architecture**: How Hybrid Search, Reranking, and Grounding works.
    *   **Solutions**: "Hard Negative" defense, Table formatting logic.
    *   **Roadmap**: Future plans (State Machine, Multi-domain).

*   **[`data/EXPERIMENT_REGISTRY.md`](./data/EXPERIMENT_REGISTRY.md)**  
    The live log of all experiments run, their configs, and metric results.

## 🛠️ Scripts

*   `evaluate_rag_faithfulness.py`: Main script to run DeepEval metrics against the current RAG pipeline.
*   `evaluate_rag.py`: Legacy evaluation script.

## 🗑️ Deprecated
Older documentation files (`rag_evaluation_report.md`, `search_quality_issues.md`, etc.) have been consolidated into `RAG_KNOWLEDGE_BASE.md`.
