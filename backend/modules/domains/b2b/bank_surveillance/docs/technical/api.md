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

## Alerts

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/alerts` | List alerts (with filters) | `surveillance:read` |
| `GET` | `/alerts/{id}` | Get alert details | `surveillance:read` |
| `PATCH` | `/alerts/{id}` | Update status (Close, Escalate) | `surveillance:write` |
| `POST` | `/alerts/{id}/case` | Convert to Case | `surveillance:write` |

### Alert List Example
```json
// GET /alerts?status=open&risk_type=insider_trading
{
  "items": [
    {
      "id": "alert-123",
      "risk_type": "insider_trading",
      "severity": "critical",
      "status": "open",
      "aggregation_count": 5
    }
  ]
}
```

---

## Policies

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/policies` | List risk policies | `policy:read` |
| `POST` | `/policies` | Create new policy | `policy:manage` |
| `PUT` | `/policies/{id}` | Update policy rules | `policy:manage` |
| `POST` | `/policies/test` | Test rules against sample | `policy:manage` |

### Regulatory Documents (Knowledge Base)
| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `POST` | `/policies/documents` | Upload PDF (MAS/SEC/FCA) | `policy:manage` |
| `GET` | `/policies/documents/{id}/citation` | Retrieve specific clause text | `policy:read` |

### Policy Feedback
| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `POST` | `/alerts/{id}/feedback` | Mark False Positive | `surveillance:write` |

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
  "text": "We need to get shorty on these California power grids. Move the load to the death star strategy.",
  "metadata": {
    "sender": "trader@bank.com",
    "risk_classifier": "market_manipulation"
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
