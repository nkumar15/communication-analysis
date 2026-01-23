# API Reference

**Base Path**: `/api/b2b/domain/bank_surveillance`

## 1. Communications & Search

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/search` | RAG Semantic Search (ES-backed) | `surveillance:read` |
| `GET` | `/messages/{id}` | Get metadata + thread context | `surveillance:read` |

---

## 2. Risk Workflows (UI Triggerable)

These endpoints initiate the background surveillance workflows.

### Workflow A: Ingest + Detect
| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `POST` | `/ingestion/trigger` | Ingest Daily Dump & Run Detection | `surveillance:admin` |

- **Payload**: `{"date": "YYYYMMDD", "file_path": "..."}`
- **Sub-tasks**: Automatically triggers `analyze_message` per record to generate **RiskEvents**.

### Workflow B: Group + Alert
| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `POST` | `/alerts/generate` | Aggregate Events into Alerts | `surveillance:admin` |

- **Payload**: `{"start_date": "...", "end_date": "..."}`
- **Process**: Groups `RiskEvents` into **Incidents** and links them to **Alerts**.

---

## 3. Alerts & Investigation

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/alerts` | List alerts (with filters) | `surveillance:read` |
| `GET` | `/alerts/{id}` | Get alert, incidents, and context | `surveillance:read` |
| `PATCH` | `/alerts/{id}` | Update status (Close, Escalate) | `surveillance:write` |
| `POST` | `/alerts/{id}/case` | Convert to Investigation Case | `surveillance:write` |

### Alert Details Example
```json
// GET /alerts/alert-abc
{
  "alert": { "id": "alert-abc", "status": "open", "severity": "high" },
  "incidents": [
    {
      "id": "inc-1",
      "sender": "trader@bank.com",
      "date": "2023-10-27",
      "risk_indicator": "Load Shifting",
      "event_count": 5
    }
  ],
  "conversation_thread": [
     { "sender": "user1", "content": "...", "is_flagged": false },
     { "sender": "user1", "content": "risky text", "is_flagged": true }
  ]
}
```

---

## 4. Surveillance Controls

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/surveillance-controls` | List detection controls | `controls:read` |
| `POST` | `/surveillance-controls` | Create control (Keywords/Regex) | `controls:manage` |
| `PUT` | `/surveillance-controls/{id}` | Update indicator/aggregation policy | `controls:manage` |

---

## 5. AI Graph Analysis

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `POST` | `/graph/build` | Rebuild network graph | `surveillance:admin` |
| `GET` | `/graph/ ego/{id}` | Get sender's network centrality | `surveillance:read` |
