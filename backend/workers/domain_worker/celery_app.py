
import os
from celery import Celery
from core.config import settings

# Initialize Celery app for Domain Worker
celery_app = Celery(
    'domain_tasks',
    broker=settings.celery_broker_url_resolved,
    backend=settings.celery_result_backend_resolved,
    include=[
        'workers.domain_worker.rag_tasks',
    ]
)

# Celery configuration (Same as b2b-worker)
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes for RAG ingestion
    task_soft_time_limit=540,
    worker_max_tasks_per_child=100, # Recycle sooner due to memory usage (ML models)
    result_expires=86400, # 24 hours
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue='domain', # Isolate domain tasks
    task_routes={
        'domain.ingest_document': {'queue': 'domain'},
    }
)

if __name__ == '__main__':
    celery_app.start()
