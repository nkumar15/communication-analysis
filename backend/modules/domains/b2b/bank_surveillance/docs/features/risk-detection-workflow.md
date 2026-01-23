# Feature: Risk Detection Workflow

> **Status**: 📝 Documented (Ready for Implementation)  
> **Module**: `bank_surveillance`  
> **Priority**: High  

---

## Summary

A 3-tier risk detection system that transforms high-volume communications into actionable analyst alerts.

```
Communication → RiskEvent → Incident → Alert
```

## Quick Reference

| Document | Path |
|----------|------|
| Architecture | [technical/architecture.md](./technical/architecture.md) |
| Database Schema | [technical/schema.md](./technical/schema.md) |
| API Reference | [technical/api.md](./technical/api.md) |

---

## Workflows

### Workflow A: Ingest + Detect
- **Trigger**: `POST /api/b2b/domain/bank_surveillance/ingestion/trigger`
- **Processing**: Celery Worker
- **Output**: `RiskEvent` records for matched messages

### Workflow B: Group + Alert
- **Trigger**: `POST /api/b2b/domain/bank_surveillance/alerts/generate`
- **Processing**: Celery Worker
- **Output**: `Incident` and `Alert` records

---

## Implementation Checklist

### New Models (Priority 1)
- [ ] `models/risk_event.py` - Individual detection match
- [ ] `models/incident.py` - Aggregated signals per sender/day

### New Services (Priority 2)
- [ ] `services/detection.py` - Keyword/Regex detection via ES
- [ ] `services/aggregation.py` - Grouping logic (Events → Incidents)

### New Tasks (Priority 3)
- [ ] `tasks/alerting.py` - Celery task for Workflow B

### Updates (Priority 4)
- [ ] `models/communication.py` - Add `analyzed`, `thread_id`, `channel`
- [ ] `models/alert.py` - Link to Incidents (1:N relationship)

### Database Migration
- [ ] Create `bank_surveillance.risk_events` table
- [ ] Create `bank_surveillance.incidents` table
- [ ] Add columns to `bank_surveillance.communications`

### API Endpoints
- [ ] `GET /risk-events` - List events
- [ ] `GET /incidents` - List incidents
- [ ] `POST /alerts/generate` - Trigger aggregation

---

## How to Implement

Tell Claude:

> **"Implement the Risk Detection Workflow feature for bank_surveillance"**

Or be specific:

> **"Implement components marked [NEW] in bank_surveillance/docs/technical/architecture.md"**

---

## Design Decisions

| Topic | Decision |
|-------|----------|
| Message Storage | ES (content) + PG (metadata) |
| Alert Hierarchy | 1 Alert : N Incidents |
| Detection | Keyword + Regex via Elasticsearch |
| Processing | Async via Celery workers |
| Thread Limit | 10 messages (demo) |

---

## Related Features (Future)

- [ ] **Tier 4: Agentic Investigation** - Intent/Policy/Evasion agents
- [ ] **Reprocessing Strategy** - Version-based control tracking
