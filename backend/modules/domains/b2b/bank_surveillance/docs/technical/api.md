# API Reference

**Base Path**: `/api/b2b/domain/bank_surveillance`

## 1. Communications & Search

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/search` | RAG Semantic Search (ES-backed) | `surveillance:read` |
| `GET` | `/messages/{id}` | Get metadata + thread context | `surveillance:read` |

---

## 2. Risk Workflows

> [!IMPORTANT]
> Workflows are **triggered via API** from the UI but **processed asynchronously by Celery workers**. The API returns a `job_id` for status tracking.

### Workflow A: Ingest + Detect
| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `POST` | `/ingestion/trigger` | Trigger ingestion + detection | `surveillance:admin` |
| `GET` | `/ingestion/status/{job_id}` | Poll job status | `surveillance:admin` |

**Request:**
```json
{ "date": "YYYYMMDD", "file_path": "/data/daily/..." }
```

**Response (202 Accepted):**
```json
{ "job_id": "abc-123", "status": "queued" }
```

**Processing (Celery Worker):**
1. Ingest file → Store content in ES, metadata in PG
2. For each message → Run detection against active controls
3. Generate `RiskEvent` records for matches

---

### Workflow B: Group + Alert
| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `POST` | `/alerts/generate` | Trigger incident/alert generation | `surveillance:admin` |

**Request:**
```json
{ "start_date": "2024-01-01", "end_date": "2024-01-31" }
```

**Response (202 Accepted):**
```json
{ "job_id": "xyz-456", "status": "queued" }
```

**Processing (Celery Worker):**
1. Fetch unprocessed `RiskEvents` in date range
2. Group by `sender + control + date` → Create `Incidents`
3. Link Incidents to new or existing `Alerts`

---

## 3. Alerts & Investigation

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/alerts` | List alerts (with filters) | `surveillance:read` |
| `GET` | `/alerts/{id}` | Get alert with incidents and thread | `surveillance:read` |
| `PATCH` | `/alerts/{id}` | Update status (Close, Escalate) | `surveillance:write` |
| `POST` | `/alerts/{id}/case` | Convert to Investigation Case | `surveillance:write` |

### Alert Details Response
```json
{
  "alert": { "id": "...", "status": "open", "severity": "high", "subject": "..." },
  "incidents": [
    { "id": "...", "sender": "trader@bank.com", "date": "2024-01-23", "event_count": 5 }
  ],
  "conversation_thread": [
    { "id": "msg-1", "sender": "...", "content": "...", "is_flagged": false },
    { "id": "msg-2", "sender": "...", "content": "...", "is_flagged": true, "matched_keywords": ["..."] }
  ]
}
```

---

## 4. Risk Events & Incidents (Audit)

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/risk-events` | List events (filter by incident_id) | `surveillance:read` |
| `GET` | `/incidents` | List incidents (filter by alert_id) | `surveillance:read` |
| `GET` | `/incidents/{id}` | Get incident with linked events | `surveillance:read` |

---

## 5. Surveillance Controls

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/surveillance-controls` | List detection controls | `controls:read` |
| `POST` | `/surveillance-controls` | Create control (Keywords/Regex) | `controls:manage` |
| `PUT` | `/surveillance-controls/{id}` | Update indicator config | `controls:manage` |

---

## 6. AI Graph Analysis

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `POST` | `/graph/build` | Rebuild network graph | `surveillance:admin` |
| `GET` | `/graph/ego/{id}` | Get sender's network centrality | `surveillance:read` |

---

## Error Responses

| Status | Meaning |
|--------|---------|
| `400` | Invalid request payload |
| `401` | Missing/invalid auth token |
| `403` | Insufficient permissions |
| `404` | Resource not found or tenant isolation |
| `422` | Validation error |
| `500` | Internal server error |
