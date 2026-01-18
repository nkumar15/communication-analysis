
import os
from celery import Celery
from core.config import settings
# Ensure models are loaded for SQLAlchemy Foreign Keys
from modules.b2c.models.user import B2CUser

# Initialize Celery app for B2C Domain Worker
celery_app = Celery(
    'b2c_domain_tasks',
    broker=settings.celery_broker_url_resolved,
    backend=settings.celery_result_backend_resolved,
    include=[
        'workers.b2c_domain_worker.rag_tasks',
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
    task_time_limit=1800,  # 30 minutes for heavy RAG ingestion
    task_soft_time_limit=1700,
    worker_max_tasks_per_child=50, # Recycle sooner due to ML memory usage
    result_expires=86400,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue='b2c-domain',
    task_routes={
        'b2c_domain.ingest_document': {'queue': 'b2c-domain'},
    }
)

if __name__ == '__main__':
    celery_app.start()
