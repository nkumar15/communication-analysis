"""
B2C Worker - Celery Application for B2C Background Jobs

Handles:
- Subscription email notifications
- Payment failure alerts
- Subscription lifecycle emails
- Invoice notifications
"""
from celery import Celery
from core.config import settings
from workers.b2c_worker.beat_schedule import beat_schedule

# Create Celery app
app = Celery(
    'b2c_worker',
    broker=settings.celery_broker_url_resolved,
    backend=settings.celery_result_backend_resolved,
    include=['workers.b2c_worker.tasks']
)

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule=beat_schedule,  # Add beat schedule
)

if __name__ == '__main__':
    app.start()
