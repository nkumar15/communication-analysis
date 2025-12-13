"""
Celery Application Configuration

This module initializes and configures the Celery application for background task processing.
Tasks include: email sending, audit log persistence, and bulk operations.
"""

from celery import Celery
from core.config import settings

# Initialize Celery app
celery_app = Celery(
    'sso_tasks',
    broker=f'redis://{settings.redis_host}:{settings.redis_port}/0',
    backend=f'redis://{settings.redis_host}:{settings.redis_port}/0',
    include=[
        'core.tasks.email_tasks',
        'core.tasks.audit_tasks',
    ]
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    
    # Worker configuration
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,  # Recycle worker after 1000 tasks
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    
    # Task routing (optional - for future use)
    task_routes={
        'core.tasks.email_tasks.*': {'queue': 'emails'},
        'core.tasks.audit_tasks.*': {'queue': 'audit'},
    },
    
    # Retry configuration
    task_acks_late=True,  # Acknowledge tasks after completion
    task_reject_on_worker_lost=True,  # Requeue tasks if worker crashes
)


if __name__ == '__main__':
    celery_app.start()
