# GenAI RAG Experimentation Framework

This guide documents how to run RAG experiments using the configuration-driven framework.

## Overview

The framework allows you to define RAG pipelines (Retriever settings, Reranker models, LLM parameters) in a YAML configuration file and run them against a standard dataset. This ensures repeatability and easy comparison between experiments.

## 1. Directory Structure

All evaluation logic is located in `backend/scripts/evaluation`:

```
backend/scripts/evaluation/
├── core/                  # Framework Logic
│   ├── config.py          # Pydantic Configuration Models
│   ├── runner.py          # Unified Evaluation Runner
│   ├── factory.py         # Component Factory
│   └── retrievers.py      # Configurable Retrievers
├── datasets/              # Evaluation Datasets (JSON)
│   └── nse/               # Project-specific datasets
├── projects/              # Experiment Configurations (YAML)
│   └── nse/               # Project-specific configs
└── results/               # Output Logs
    └── nse/               # JSON results
```

## 2. Defining an Experiment

Create a YAML file in `backend/scripts/evaluation/projects/<project>/<name>.yaml`.

**Example (`experiment_v1.yaml`):**
```yaml
name: "nse_hybrid_v1"
description: "Baseline Hybrid Search with Reranking"
tenant_id: "05b51fa4-45f4-50c2-b3f4-4c122000347b"
dataset_path: "scripts/evaluation/datasets/nse/gold_dataset.json"
output_dir: "scripts/evaluation/results/nse"

metrics:
  - faithfulness
  - answer_relevancy
  - contextual_recall

pipeline:
  retriever:
    type: "hybrid"        # Options: "hybrid", "vector" (future)
    top_k: 20             # Candidates to retrieve before reranking
    index_name: "nse_rag_documents"
    
  reranker:
    enabled: true
    model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_n: 5              # Final results passed to LLM
    
  llm:
    model: "gpt-4o-mini"
    temperature: 0.0
```

## 3. Running an Experiment

Use the `make eval-run` target. This runs the evaluation inside the `e2e-tests` Docker container to ensure all dependencies are available.

```bash
# Run from project root
make eval-run CONFIG=scripts/evaluation/projects/nse/experiment_v1.yaml
```

**Note:** The `CONFIG` path is relative to the `backend/` directory (which is mounted as `/app` inside the container).

## 4. Analyzing Results

Results are saved as JSON files in the configured `output_dir` (default: `scripts/evaluation/results/<project>/`).

**File Format:** `<experiment_name>_<timestamp>.json`

**Content:**
- **Config**: A copy of the experiment configuration used.
- **Metrics**: Aggregated scores (Faithfulness, Relevancy, Recall).
- **Results**: Detailed breakdown of each test case (Query, Retrieved Context, Actual Answer, Scores).

## 5. Adding New Projects

To support a new project (e.g., "Enron"):
1. Create `backend/scripts/evaluation/projects/enron/`.
2. Create `backend/scripts/evaluation/datasets/enron/`.
3. Add your dataset JSON.
4. Create a config YAML pointing to your dataset and Tenant ID.
