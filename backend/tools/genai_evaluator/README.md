# GenAI Evaluator Tool

## 1. Overview
The GenAI Evaluator is a specialized internal tool designed to run Retrieval Augmented Generation (RAG) experiments and evaluate their performance using metrics like Faithfulness, Answer Relevancy, and Contextual Recall. It supports multiple projects (e.g., Enron, NSE) and allows for rapid iteration on retrieval strategies and prompt engineering.

## 2. Setup

### Prerequisites
- Python 3.11+
- `deepeval` library
- OpenAI API Key (or other LLM provider configured)
- Project dependencies installed

### Installation
The tool relies on the backend environment. Ensure you are in the root and dependencies are installed.

```bash
# Install additional ML dependencies if not present
pip install deepeval sentence-transformers
```

## 3. Usage

### Basic Command
Run an evaluation experiment using the `runner` module.

```bash
# From repository root
python -m tools.genai_evaluator.core.runner --config tools/genai_evaluator/projects/enron/config.yaml
```

### Arguments
| Argument | Description | Required | Default |
| :--- | :--- | :--- | :--- |
| `--config` | Path to the experiment configuration YAML file. | Yes | - |
| `--update-registry` | If set, updates `EXPERIMENT_REGISTRY.md` with the results. | No | False |

## 4. Configuration
Experiments are defined in YAML files.

**Example Structure**:
```yaml
name: "enron_baseline_v1"
description: "Baseline RAG with Hybrid Search"
tenant_id: "05b51fa4-45f4-50c2-b3f4-4c122000347b"
dataset_path: "../../datasets/enron/golden_dataset/golden_set.json"

pipeline:
  retriever:
    type: "hybrid"  # vector, bm25, or hybrid
    top_k: 20
    index_name: "enron_documents"
    weights: [0.5, 0.5]
  
  reranker:
    enabled: true
    model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_n: 10

  llm:
    model: "gpt-4o-mini"
    temperature: 0.0
    prompt_strategy: "grounding_cot"

metrics:
  - "faithfulness"
  - "answer_relevancy"
  - "contextual_recall"
```

## 5. Architecture

### Components
- **Core (`core/`)**:
    - `runner.py`: Orchestrates the experiment (Load Data -> Retrieve -> Synthesize -> Evaluate).
    - `factory.py`: Instantiates RAG components (Retriever, LLM) dynamically.
    - `config.py`: Pydantic models for configuration validation.
- **Projects (`projects/`)**:
    - Contains project-specific configurations and datasets (e.g., `enron/`, `nse/`).
    - `EXPERIMENT_REGISTRY.md`: Tracks experiment history.

### Data Flow
1.  **Loader**: Reads `dataset_path` (JSON).
2.  **Retriever**: Fetches nodes using `TenantAwareHybridRetriever`.
3.  **Reranker**: (Optional) Re-scores nodes using CrossEncoder.
4.  **Synthesizer**: Generates answer using LLM.
5.  **Evaluator**: `deepeval` computes metrics comparing Actual vs Expected/Context.
6.  **Logger**: Saves details to JSON and updates Registry.

## 6. Output
Results are saved to the `results/` directory (or specific project results folder).

**File Format**: `[ExperimentName]_[Timestamp].json`
```json
{
  "experiment": "enron_baseline_v1",
  "timestamp": "2026-01-19T12:00:00",
  "metrics": {
    "Faithfulness": 0.95,
    "Answer Relevancy": 0.88,
    "Contextual Recall": 0.92
  },
  "results": [
    {
      "input": "...",
      "actual_output": "...",
      "metrics": { ... }
    }
  ]
}
```
