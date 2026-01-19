
import os
from celery import Celery
from core.config import settings

# Initialize Celery app for B2B Domain Worker
celery_app = Celery(
    'b2b_domain_tasks',
    broker=settings.celery_broker_url_resolved,
    backend=settings.celery_result_backend_resolved,
    include=[
        # Include B2B domain tasks here in the future
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_max_tasks_per_child=100,
    result_expires=86400,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue='b2b-domain',
)

if __name__ == '__main__':
    celery_app.start()
