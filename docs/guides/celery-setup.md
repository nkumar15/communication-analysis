# Celery Background Task Setup

## Installation

```bash
# requirements.txt
celery[redis]==5.3.4
redis==5.0.1
```

## Configuration

```python
# core/tasks/celery_app.py
from celery import Celery
from core.config import settings

# Initialize Celery
celery_app = Celery(
    'sso_tasks',
    broker=f'redis://{settings.redis_host}:{settings.redis_port}/0',
    backend=f'redis://{settings.redis_host}:{settings.redis_port}/0'
)

# Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)
```

## Task Definitions

```python
# core/tasks/email_tasks.py
from workers.b2b_worker.celery_app import celery_app
from core.database import AsyncSessionLocal
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import asyncio

@celery_app.task(bind=True, max_retries=3)
def send_invitation_email(self, invitation_id: str, tenant_id: str):
    """Send individual invitation email (sync wrapper for async code)"""
    asyncio.run(_send_invitation_email_async(invitation_id, tenant_id))


async def _send_invitation_email_async(invitation_id: str, tenant_id: str):
    """Async implementation"""
    async with AsyncSessionLocal() as db:
        try:
            from services.b2b.models import InvitationModel
            from core.email import email_service
            from datetime import datetime
            
            # Fetch invitation
            result = await db.execute(
                select(InvitationModel)
                .options(selectinload(InvitationModel.tenant))
                .where(InvitationModel.id == invitation_id)
            )
            invitation = result.scalar_one_or_none()
            
            if not invitation:
                return
            
            # Send email
            await email_service.send_invitation_email(
                to_email=invitation.email,
                invitation_token=invitation.invitation_token,
                tenant_name=invitation.tenant.name,
                expires_at=invitation.expires_at
            )
            
            # Update status
            invitation.email_sent_at = datetime.utcnow()
            await db.commit()
            
        except Exception as e:
            await db.rollback()
            raise


@celery_app.task(bind=True, max_retries=2)
def send_bulk_invitation_emails(self, invitation_ids: list, tenant_id: str):
    """Send multiple invitation emails"""
    asyncio.run(_send_bulk_invitation_emails_async(invitation_ids, tenant_id))


async def _send_bulk_invitation_emails_async(invitation_ids: list, tenant_id: str):
    """Async implementation"""
    async with AsyncSessionLocal() as db:
        # Implementation same as before...
        pass
```

```python
# core/tasks/audit_tasks.py
from workers.b2b_worker.celery_app import celery_app
from core.database import AsyncSessionLocal
import asyncio

@celery_app.task(bind=True, max_retries=3)
def persist_audit_log(
    self,
    tenant_id: str,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict
):
    """Persist audit log entry"""
    asyncio.run(_persist_audit_log_async(
        tenant_id, user_id, action, resource_type, resource_id, metadata
    ))


async def _persist_audit_log_async(
    tenant_id: str,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict
):
    """Async implementation"""
    async with AsyncSessionLocal() as db:
        try:
            from services.b2b.models import AuditLog
            
            audit_entry = AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=metadata,
                ip_address=metadata.get('ip_address'),
                user_agent=metadata.get('user_agent')
            )
            
            db.add(audit_entry)
            await db.commit()
            
        except Exception as e:
            await db.rollback()
            raise
```

## Usage in Code

```python
# services/b2b/routers/invitations.py
from workers.b2b_worker.email_tasks import send_invitation_email, send_bulk_invitation_emails

@router.post("/invitations/bulk")
async def bulk_invite_users(...):
    # Create invitations
    invitations = await invitation_service.bulk_create_invitations(...)
    await db.commit()
    
    # Queue emails (Celery)
    invitation_ids = [str(inv.id) for inv in invitations]
    send_bulk_invitation_emails.delay(invitation_ids, str(tenant_id))
    
    return {"success": True}


# services/b2b/services/audit_service.py
from workers.b2b_worker.audit_tasks import persist_audit_log

async def log_action(tenant_id, user_id, action, resource_type, resource_id, metadata):
    """Log action asynchronously"""
    persist_audit_log.delay(
        str(tenant_id),
        str(user_id),
        action,
        resource_type,
        str(resource_id),
        metadata
    )
```

## Running Celery Worker

```bash
# Development
celery -A workers.b2b_worker.celery_app worker --loglevel=info

# Production (with autoscaling)
celery -A workers.b2b_worker.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --autoscale=10,3 \
  --max-tasks-per-child=1000

# Docker (already in docker-compose.yml)
docker-compose up celery-worker
```

## Monitoring with Flower

```bash
# Install Flower
pip install flower

# Run dashboard
celery -A workers.b2b_worker.celery_app flower --port=5555

# Access at http://localhost:5555
```

## Key Differences from ARQ

### ARQ (old):
```python
async def send_email(ctx, email_id):
    # task code

# Run worker
arq workers.b2b_worker.celery_app.WorkerSettings
```

### Celery (new):
```python
@celery_app.task
def send_email(email_id):
    asyncio.run(_send_email_async(email_id))

async def _send_email_async(email_id):
    # async task code

# Run worker
celery -A workers.b2b_worker.celery_app worker
```

## Benefits

✅ **Production-ready** - Used by major companies
✅ **Active maintenance** - Won't be abandoned
✅ **Rich monitoring** - Flower dashboard
✅ **Proven scalability** - Handles millions of tasks
✅ **BSD license** - Very permissive, commercial-friendly
