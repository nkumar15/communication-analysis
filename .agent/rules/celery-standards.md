---
trigger: always_on
---

# Celery Standards

## Scope
Owned by: **Backend Architect**
Applies to: **Background Tasks, Queues, Workers**

## 1. Task Arguments
- **ONLY pass primitive IDs** (UUID strings, ints) to tasks — never SQLAlchemy model instances.
- **Why**: Celery serializes arguments to JSON/pickle. ORM objects carry DB sessions that are invalid across process boundaries and cause subtle corruption bugs.

```python
# ✅ Correct
persist_audit_log.delay(str(tenant_id), str(actor_id), event_type, str(resource_id))

# ❌ Wrong — never pass ORM objects
persist_audit_log.delay(user_obj, tenant_obj)
```

## 2. Task Naming Convention
Format: `{module}.{domain}.{noun}_{verb}`

| Module | Domain | Example |
|--------|--------|---------|
| `b2b` | `iam` | `b2b.iam.audit_log_persist` |
| `b2b` | `billing` | `b2b.billing.invoice_send` |
| `b2b_domain` | `bank_surveillance` | `b2b_domain.bank_surveillance.email_ingest` |
| `b2c` | `workspace` | `b2c.workspace.member_notify` |

Define task names explicitly with `name=` — never rely on auto-generated names, which break on refactor:
```python
@celery_app.task(name="b2b.iam.audit_log_persist", bind=True)
def persist_audit_log(self, tenant_id: str, actor_id: str, ...):
    ...
```

## 3. Queue Assignment
Each worker owns a dedicated queue — never cross-publish:

| Queue | Worker | Task Types |
|-------|--------|-----------|
| `b2b` | `b2b_worker` | IAM, billing, teams, invitations |
| `b2b_domain` | `b2b_domain_worker` | Surveillance ingestion, indexing, AI pipelines |
| `b2c` | `b2c_worker` | Workspace, subscriptions |
| `b2c_domain` | `b2c_domain_worker` | Domain-specific B2C tasks |

```python
persist_audit_log.apply_async(args=[...], queue="b2b")
```

## 4. Idempotency
All tasks **MUST** be safe to retry without side effects:
- Check existence before creating (e.g., `SELECT … FOR UPDATE` then upsert).
- Use a unique idempotency key (e.g., `(tenant_id, resource_id, event_type)`) for audit logs and emails.
- For email tasks: check a `sent_at` flag before sending.

## 5. Retry Policy
Use exponential backoff. Never use bare `retry()` without limits:

```python
@celery_app.task(
    name="b2b.billing.invoice_send",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # seconds
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_invoice(self, tenant_id: str, invoice_id: str):
    ...
```

- `max_retries=3` for transient failures (email, webhook).
- `max_retries=0` (no retry) for tasks that must not duplicate (e.g., payment capture).

## 6. Trigger Timing
Tasks must be triggered from the **Router layer AFTER `await db.commit()`**, not from services:

```python
# ✅ Correct — in router, after commit
await db.commit()
persist_audit_log.apply_async(args=[str(tenant_id), ...], queue="b2b")

# ❌ Wrong — inside service (DB may not be committed yet)
def create_user(...):
    db.add(user)
    persist_audit_log.delay(...)  # Fires before commit
```

## 7. Long-Running Tasks
For tasks that take >30s (e.g., ingestion, bulk exports):
- Return a Job ID immediately from the API (`202 Accepted`).
- Update a `job_status` record (`PENDING → RUNNING → DONE/FAILED`) in the DB.
- Never block the HTTP request waiting for task completion.

## 8. Monitoring
- All tasks should log start and completion at `INFO` level with `task_id`, `tenant_id`.
- Log failures at `ERROR` with `exc_info=True`.
- Never log PII (email addresses, names) in task logs.

```python
logger = get_logger(__name__)

def my_task(self, tenant_id: str, resource_id: str):
    logger.info("task_started", task_id=self.request.id, tenant_id=tenant_id)
    try:
        ...
        logger.info("task_completed", task_id=self.request.id, tenant_id=tenant_id)
    except Exception as exc:
        logger.error("task_failed", task_id=self.request.id, exc_info=True)
        raise
```

## 9. Scheduled Tasks (Celery Beat)
- Define scheduled tasks in `workers/{module}_worker/beat_schedule.py`, not inline in `celery_app` config.
- Use `crontab()` expressions, not raw seconds, for readability.
- All beat tasks must be idempotent (they will fire even if the previous run is still in-flight).
