# API Reference

**Base Path**: `/api/b2b/domain/bank_surveillance`

## Communications (Messaging)

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/search` | RAG Semantic Search | `surveillance:read` |
| `GET` | `/messages/{id}` | Get raw message content | `surveillance:read` |

### Search Example
```json
// GET /search?q=earnings+leak&limit=10
{
  "results": [
    {
      "id": "msg-uuid",
      "relevance": 0.92,
      "text": "...discussing quarterly earnings...",
      "metadata": {
         "sender": "trader@bank.com",
         "timestamp": "2023-10-27T10:00:00Z"
      }
    }
  ]
}
```

---

## Investigations (AI Agents)

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `POST` | `/investigate` | Run Multi-Agent Analysis | `surveillance:write` |
| `POST` | `/cases` | Create Investigation Case | `surveillance:write` |

### Investigate Payload
```json
// POST /investigate
{
  "text": "Let's hide this transaction in the SPV",
  "metadata": {
    "sender": "trader@bank.com"
  }
}
```

---

## Graph Analysis

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `POST` | `/graph/build` | Rebuild network graph | `surveillance:admin` |
| `GET` | `/graph/summary` | Get graph stats | `surveillance:read` |
| `GET` | `/graph/cliques` | Detect collusion rings | `surveillance:read` |
| `GET` | `/graph/ego/{target}` | Get target's network | `surveillance:read` |

### Ego Network Example
```json
// GET /graph/ego/trader@bank.com
{
  "center": "trader@bank.com",
  "connections": [
    {"target": "manager@bank.com", "weight": 45},
    {"target": "outsider@gmail.com", "weight": 23}
  ],
  "centrality": 0.78
}
```

---

## Ingestion (Async Pipeline)

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `POST` | `/ingestion/trigger` | Manually trigger daily dump ingestion | `surveillance:admin` |
| `GET` | `/ingestion/status/{job_id}` | Get status of ingestion job | `surveillance:admin` |
| `POST` | `/ingestion/retry/{job_id}` | Retry failed file segments | `surveillance:admin` |

### Trigger Payload
```json
// POST /ingestion/trigger
{
  "date": "20231027",
  "force": false
}
```
