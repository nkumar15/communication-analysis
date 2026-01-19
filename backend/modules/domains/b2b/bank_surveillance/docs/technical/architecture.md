# Architecture

## Data Flow

```mermaid
graph TD
    A[Compliance Officer] -->|POST /investigate| B(API)
    B -->|Content| C[Orchestrator]
    C -->|Parallel| D[Intent Agent]
    C -->|Parallel| E[Policy Agent]
    C -->|Parallel| F[Evasion Agent]
    C -->|Results| G[Investigation Report]
    G -->|Enrich| H[Graph Service]
    H -->|Ego Network| G

    I[IT Admin] -->|POST /ingestion| B
    B -->|Async Task| J[Celery Worker]
    J -->|File Read| K[Ingestion Service]
    K -->|Store| L[(Postgres)]
    K -->|Index| M[Elasticsearch]
    M -->|Vectors| N[RAG Service]
```

## Key Components

| Component | File | Description |
| :--- | :--- | :--- |
| **API** | `routers/communications.py` | Message CRUD & Search Endpoints |
| **API** | `routers/investigations.py` | AI Analysis & Agent Coordination |
| **API** | `routers/graph.py` | Network Analysis Endpoints |
| **API** | `routers/ingestion.py` | Ingestion Trigger & Status |
| **Service** | `services/orchestrator.py` | Coordinates AI Agents & Case Assembly |
| **Service** | `services/graph.py` | NetworkX Logic (Cliques, Centrality) |
| **Service** | `services/rag.py` | Vector Search over Communications |
| **Service** | `services/ingestion.py` | ETL Logic for Daily Dumps |
| **Worker** | `tasks/ingestion.py` | Celery Background Task |
| **Model** | `models/investigation.py` | Case Management Entity |
| **Model** | `models/communication.py` | Unified Message Entity (Email/Chat) |
| **Model** | `models/ingestion_log.py` | ETL Job Status Tracking |

## Dependencies

- **AI/LLM**: `langchain`, `openai` (via Agents)
- **Graph**: `networkx` (In-memory analysis of communication patterns)
- **Vector DB**: `pgvector` (via Postgres 15+)
- **Search**: `Elasticsearch` 8.x (Vector Store for RAG via LlamaIndex)
- **Queue**: `Celery` + `Redis` (Async Ingestion)
- **Schedule**: `Celery Beat` (Daily Cron)
