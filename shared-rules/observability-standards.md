---
trigger: always_on
---

# Observability Standards

## Scope
Owned by: **Platform Engineer**
Applies to: **Logging, Tracing, Metrics** across all backend services and workers

---

## 1. Logger Initialization
Always import from `infrastructure.logging`. `print()` and stdlib `logging` are forbidden in production code.

```python
from infrastructure.logging import get_logger
logger = get_logger(__name__)
```

## 2. Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| `DEBUG` | Internal state useful during development only | Query parameters, intermediate computed values |
| `INFO` | Normal lifecycle events | Request received, task started, resource created |
| `WARNING` | Unexpected but recoverable state | Retry attempt, config fallback used, deprecated API called |
| `ERROR` | Failure requiring investigation | Unhandled exception, external API failure, DB constraint violation |
| `CRITICAL` | System-level failure impacting availability | Cannot connect to DB, queue unreachable at startup |

```python
logger.info("user_created", user_id=str(user.id), tenant_id=str(tenant_id))
logger.warning("stripe_retry", attempt=attempt, tenant_id=str(tenant_id))
logger.error("payment_failed", invoice_id=str(invoice_id), exc_info=True)
```

## 3. Structured Log Fields
Use keyword arguments (structured logging), never f-strings or % formatting for log messages:

```python
# ✅ Correct — structured, searchable
logger.info("invitation_sent", invitation_id=str(inv.id), tenant_id=str(tenant_id))

# ❌ Wrong — unstructured, unsearchable
logger.info(f"Invitation {inv.id} sent to {email}")  # Also leaks PII
```

### Required Fields by Context

| Context | Required Fields |
|---------|----------------|
| API Request | `tenant_id`, `user_id`, `request_id` (from middleware) |
| Celery Task | `task_id`, `tenant_id` |
| Billing Event | `tenant_id`, `plan_id`, `event_type` |
| Auth Event | `tenant_id`, `event_type` (never log tokens or passwords) |

## 4. PII Redaction
**Never log** the following — replace with IDs or omit entirely:
- Email addresses
- Full names
- Phone numbers
- IP addresses (log only if explicitly required for security audit, and only masked)
- Auth tokens, API keys, passwords, or any secret material
- Payment card details

```python
# ❌ Leaks PII
logger.info("invite_created", email=invite.email, name=invite.full_name)

# ✅ Safe
logger.info("invite_created", invite_id=str(invite.id), tenant_id=str(tenant_id))
```

## 5. OpenTelemetry Tracing
The `infrastructure/monitoring` module instruments FastAPI and SQLAlchemy automatically. For custom spans in services:

```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

async def process_surveillance_alert(alert_id: str, tenant_id: str):
    with tracer.start_as_current_span("surveillance.alert.process") as span:
        span.set_attribute("alert.id", alert_id)
        span.set_attribute("tenant.id", tenant_id)
        ...
```

### Span Naming Convention
Format: `{domain}.{resource}.{action}` (lowercase, dot-separated)

| Good | Bad |
|------|-----|
| `b2b.user.create` | `createUser` |
| `bank_surveillance.email.ingest` | `IngestEmail` |
| `billing.subscription.update` | `update_subscription` |

### What to Add as Span Attributes
- `tenant.id` — always, for any tenant-scoped operation
- `resource.id` — the primary entity being acted on
- `user.id` — when user-initiated
- Never add PII as span attributes

## 6. Prometheus Metrics
Custom metrics are defined in `infrastructure/monitoring`. Follow these conventions:

### Naming
Format: `{service}_{subsystem}_{metric_name}_{unit}`

```python
# ✅ Correct
b2b_invitations_sent_total
b2b_billing_stripe_latency_seconds
bank_surveillance_alerts_processed_total

# ❌ Wrong
inviteSent, billing_call, alertsDone
```

### Metric Types
| Type | Use For |
|------|---------|
| `Counter` | Events that only go up (requests, errors, tasks completed) |
| `Histogram` | Latency, request duration, payload sizes |
| `Gauge` | Current state (active sessions, queue depth, connected tenants) |

### Labels
- Always include `tenant_id` label for per-tenant metrics.
- Keep label cardinality low — never use free-text fields (email, name, UUID) as labels.

## 7. Sentry Error Tracking
Unhandled exceptions are captured automatically via the Sentry middleware. For explicit capture:

```python
import sentry_sdk

try:
    await risky_operation()
except ExternalServiceError as exc:
    sentry_sdk.capture_exception(exc)
    logger.error("external_service_failed", exc_info=True)
    raise
```

- Set `sentry_sdk.set_tag("tenant_id", str(tenant_id))` in request context for grouping.
- Do not capture expected business exceptions (404, 403) — only unexpected failures.

## 8. Correlation IDs
The request middleware injects a `request_id` into every log record and OpenTelemetry trace. Never generate your own request IDs — rely on the middleware-provided one.

To pass correlation IDs into Celery tasks:
```python
from infrastructure.monitoring import get_current_trace_id

persist_audit_log.apply_async(
    args=[str(tenant_id), ...],
    headers={"trace_id": get_current_trace_id()},
    queue="b2b",
)
```
