# Audit Logs Settings

> **Status**: ![Status](https://img.shields.io/badge/Status-Complete-green)

Comprehensive immutable audit trails for security and compliance.

## Quick Reference
- [Technical Spec](../technical/architecture.md#observability)
- [API Reference](../technical/api.md#audit-logs)

## Overview
The Audit Log system captures every state-changing action within a tenant. It provides a historical record of "Who did What, When, and to Which Resource".
- **Immutable**: Logs cannot be modified after creation.
- **Async Persistence**: Low-latency logging via Celery backgroud tasks.
- **Context-Aware**: Captures Actor, Tenant, IP Address, and User Agent.

## Workflows

### 1. Log Event
**Trigger**: Service performs a Create/Update/Delete action.
**Process**:
1.  Service calls `audit_service.log_event()`.
2.  Log object is added to DB session.
3.  Committed atomically with the transaction.
**Output**: New row in `audit_logs` table.

### 2. View Logs
**Trigger**: Admin views "Audit Logs" page.
**Process**: API fetches logs filtered by `tenant_id` (RLS enforced).
**Output**: Paginated list of events.

## Implementation Checklist
- [x] `audit_logs` table with partitioning support
- [x] `AuditService` with async support
- [x] Integration with critical services (Auth, Billing, Team)
- [x] API Endpoint `GET /audit-logs`

## Design Decisions
| Decision | Rationale |
| :--- | :--- |
| **Sync vs Async** | Currently synchronous for strict consistency (Unit of Work), but designed for async offloading if needed. |
| **JSONB Details** | `details` column allows flexible schema for different event types (e.g., diffs for updates). |

## How to Implement

- [ ] **Inject Service**: Add `audit_service` dependency to your Router/Service.
- [ ] **Call Log**: `await audit_service.log_event(tenant_id, "resource.action", "resource_type", ...)`
- [ ] **Verify**: Check `audit_logs` table for the entry.
