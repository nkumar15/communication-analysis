# Enron Learning POC: Financial Misconduct Surveillance
> **Goal**: Master GenAI, Agents, and RAG architectures by building a "Financial Misconduct Surveillance System" using the Enron dataset as a proxy for proprietary financial data.

## 1. Core Philosophy: The Learning Bridge
This POC is designed to map public Enron data concepts directly to private financial surveillance needs. This allows us to build and test sophisticated AI architectures without needing sensitive real-world data immediately.

| Financial Misconduct Concept | Enron Dataset Proxy | AI Learning Goal |
| :--- | :--- | :--- |
| **Regulatory Policy Checking** | Checking emails against SEC Rule 10b-5 & Accounting Standards | **RAG**: Embedding complex legal texts, hybrid search, citation mapping. |
| **Historical Case Lookups** | Finding "similar" emails to known Enron fraud (e.g., Raptor SPV) | **RAG**: Case-based reasoning, similarity search, dense retrieval. |
| **Intent Analysis** | Detecting "hedging vs. speculation" or "market manipulation" | **Agents**: Single-turn classification, prompt engineering, structured output. |
| **Evasion Detection** | Detecting "Take this offline" / "Delete this" patterns | **Agents**: Nuance detection, slang/code-word identification. |
| **Collusion Networks** | Mapping Trader A $\leftrightarrow$ Broker B relationships | **Graph/Orchestration**: Multi-step reasoning, network analysis helpers. |
| **Investigation Assembly** | Auto-generating a case timeline and evidence pack | **Orchestration**: Multi-agent coordination (Planner, Retriever, Writer). |

---

## 2. Architecture Patterns (The "What We Will Build")

### Pattern A: The "Knowledge Base" (RAG)
**Objective**: Build a system that can "read" rules and past cases to inform current analysis.

*   **Component 1: Policy RAG**
    *   **Data**: Public SEC Acts (Securities Exchange Act of 1934), Sarbanes-Oxley snippets.
    *   **Task**: "Does this email discussion about 'hiding debt' violate specific accounting rules?"
    *   **Tech**: Vector Database (`pgvector` or `Qdrant`), Text Chunking (Legal hierarchy aware).

*   **Component 2: Case RAG (Few-Shot)**
    *   **Data**: A curated set of ~20-50 "labeled" Enron emails (e.g., specific emails from the Skilling/Fastow trials).
    *   **Task**: "Has this kind of 'creative structure' discussion happened before?"
    *   **Tech**: Metadata filtering (Date, Sender), Semantic Similarity.

### Pattern B: The "Smart Analyst" (Agents)
**Objective**: Build specialized agents that perform specific cognitive tasks better than a generic LLM.

*   **Agent 1: The Intent Classifier**
    *   **Role**: Triage. Reads every email.
    *   **Logic**: Classifies intent into `[Business_As_Usual, Personal, Stress/Panic, Suspicious_Activity, Evasion_Attempt]`.
    *   **Output**: Structured JSON with confidence scores.

*   **Agent 2: The Evasion Hunter**
    *   **Role**: Specialist. Looks specifically for channel-switching attempts.
    *   **Keywords/Concepts**: "burner phone", "personal email", "don't put in writing", "delete after reading".

### Pattern C: The "Investigation Team" (Orchestration)
**Objective**: Combine tools to perform a multi-step investigation.

*   **Workflow**:
    1.  **Trigger**: Intent Agent flags an email as "Suspicious".
    2.  **Scope**: **Graph Agent** finds all emails between these participants in the surrounding ±2 weeks.
    3.  **Context**: **Policy Agent** checks if the discussed topic violates rules.
    4.  **Report**: **Writer Agent** compiles a PDF "Evidence Pack" with a timeline and cited violations.

---

## 3. Implementation Stack (The "How")

Keep the stack lightweight to focus on AI logic, not infrastructure.

*   **Backend**: Python `FastAPI` (Easy to expose agents as APIs).
*   **Orchestration**: `LlamaIndex` (Strong for RAG) or `LangChain` / `LangGraph` (Strong for flows).
*   **Database**: `PostgreSQL` (Stores metadata) + `Elasticsearch` (Stores embeddings and enables vector search).
*   **Frontend**: Integrated into existing **B2B UI** (Dashboard to view "Flagged Cases", "Chat with Data", and investigation reports).
*   **Data Source**: Enron Email Dataset (Kaggle version or CMU), parsed into a clean SQL schema.

---

## 4. Development Methodology: Experiment-Driven

**All development for the Enron project MUST follow an experiment-driven approach using the existing `backend/scripts/evaluation` framework.**

### Evaluation Framework Structure
*   **Config-based**: Each experiment defined in YAML (see existing NSE project structure)
*   **Datasets**: Test cases with inputs, expected outputs, and context stored in `scripts/evaluation/datasets/`
*   **Projects**: Project-specific configurations in `scripts/evaluation/projects/enron/`
*   **Runners**: Core evaluation engine (`scripts/evaluation/core/runner.py`) with support for:
    *   DeepEval metrics (Faithfulness, Answer Relevancy, Contextual Recall)
    *   Custom retrievers and rerankers
    *   Automatic result logging and registry updates

### Experiment Workflow
1.  **Define Test Cases**: Create JSON dataset with queries, expected outputs, and ground truth context
2.  **Create Config**: Write YAML config specifying pipeline (retriever, reranker, LLM), metrics, dataset path
3.  **Run Experiment**: Execute via `python scripts/evaluation/core/runner.py --config <path> --update-registry`
4.  **Analyze Results**: Review metrics, identify failure modes, iterate on prompts/retrievers
5.  **Document**: Update experiment registry with findings and decisions

### Why This Matters
*   **Reproducibility**: Every agent/RAG iteration is versioned and measurable
*   **Comparability**: Can systematically compare "Intent Agent v1" vs "v2" with concrete metrics
*   **Knowledge Transfer**: Same framework used for NSE earnings analysis → directly applicable to financial surveillance

---

## 5. Development Roadmap

### Phase 1: Data & Foundations (Weeks 1-2)
*   [ ] **Ingestion**: Script to parse raw Enron files into Postgres (`sender`, `recipient`, `body`, `date`).
*   [ ] **Vector Store**: Set up embeddings for a subset of emails (e.g., the "Executive" folder).
*   [ ] **Basic RAG**: Chat interface to "Ask Enron" questions ("What did Fastow say about LJM?").

### Phase 2: The Agents (Weeks 3-4)
*   [ ] **Build Intent Agent**: Test prompts to reliably catch the "Raptor" discussions.
*   [ ] **Build Policy RAG**: Ingest SEC Rule 10b-5 and test checking emails against it.
*   [ ] **Build Evasion Agent**: focused red-teaming on "hiding" language.

### Phase 3: The Orchestrator (Weeks 5-6)
*   [ ] **Investigation Workflow**: Stitch agents together. Input: "Suspect Name" -> Output: "Case Report".
*   [ ] **Dashboard**: UI to view the auto-generated reports.

---

## 6. Success Metrics (Did we learn?)

**Quantifiable Metrics** (via `backend/scripts/evaluation`):
*   **Faithfulness** ≥ 70%: Agents cite actual evidence, no hallucinations
*   **Answer Relevancy** ≥ 75%: Responses directly address the query
*   **Contextual Recall** ≥ 70%: Retrieved context covers ground truth information
*   **Known Case Detection**: System flags ≥ 80% of labeled "fraud" emails from trial transcripts

**Qualitative Metrics**:
*   **Transferability**: Can swap "SEC Rules" with "Internal Bank Policy" and maintain performance (>90% metrics retention)
*   **Modularity**: Each agent (Intent, Evasion, Policy) is independently testable via evaluation framework
*   **Learning Outcome**: Can articulate design decisions backed by experiment results (captured in `EXPERIMENT_REGISTRY.md`)
