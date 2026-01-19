# API Reference

**Base Path**: `/api/b2b/domain/bank_surveillance`

## Search & RAG

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/search` | RAG Search with semantic retrieval | `surveillance:read` |
| `POST` | `/investigate` | Run AI Analysis on email | `surveillance:write` |
| `GET` | `/emails/{id}` | Get raw email by ID | `surveillance:read` |

### Search Example
```json
// GET /search?query=earnings+leak&limit=10
{
  "results": [
    {
      "id": "email-uuid",
      "relevance": 0.92,
      "snippet": "...discussing quarterly earnings...",
      "sender": "sender@enron.com"
    }
  ],
  "ai_synthesis": "Found 10 emails discussing earnings..."
}
```

---

## Graph Analysis

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `POST` | `/graph/build` | Rebuild social network | `surveillance:admin` |
| `GET` | `/graph/summary` | Get graph stats (nodes/edges) | `surveillance:read` |
| `GET` | `/graph/cliques` | Detect collusion rings | `surveillance:read` |
| `GET` | `/graph/ego/{email}` | Get user's network | `surveillance:read` |

### Ego Network Example
```json
// GET /graph/ego/john.doe@enron.com
{
  "center": "john.doe@enron.com",
  "connections": [
    {"email": "jane@enron.com", "weight": 45},
    {"email": "bob@enron.com", "weight": 23}
  ],
  "centrality": 0.78
}
```

---

## Investigations

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/investigations` | List investigations | `surveillance:read` |
| `POST` | `/investigations` | Create investigation | `surveillance:write` |
| `GET` | `/investigations/{id}` | Get investigation detail | `surveillance:read` |
| `PUT` | `/investigations/{id}` | Update investigation | `surveillance:write` |

---

## Alerts

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/alerts` | List alerts with filters | `surveillance:read` |
| `GET` | `/alerts/{id}` | Get alert detail | `surveillance:read` |
| `POST` | `/alerts/{id}/escalate` | Escalate alert | `surveillance:write` |
| `POST` | `/alerts/{id}/close` | Close alert | `surveillance:write` |

---

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Validation error |
| 401 | Unauthorized - no token |
| 403 | Forbidden - insufficient permissions |
| 404 | Resource not found |
| 422 | Unprocessable entity |
