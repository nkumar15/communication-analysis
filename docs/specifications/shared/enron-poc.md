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
*   **Database**: `PostgreSQL` (Stores metadata) + `pgvector` (Stores embeddings).
*   **Frontend**: `Streamlit` or `Next.js` (Simple dashboard to view "Flagged Cases" and "Chat with Data").
*   **Data Source**: Enron Email Dataset (Kaggle version or CMU), parsed into a clean SQL schema.

---

## 4. Development Roadmap

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

## 5. Success Metrics (Did we learn?)
*   **Transferability**: Can we swap the "SEC Rules" text with "Internal Bank Policy" text and have it still work? (Yes/No)
*   **Modularity**: Is the "Evasion Agent" a standalone python class we can lift-and-shift?
*   **Accuracy**: Does the system actually flag the *known* Enron fraud cases (e.g., identifiable emails from the trial)?
