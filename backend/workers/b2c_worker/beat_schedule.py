"""
Celery Beat Schedule Configuration for B2C Worker

Periodic tasks for subscription management.
"""
from celery.schedules import crontab

# Celery Beat schedule
beat_schedule = {
    # Check for expired grace periods daily at 3 AM UTC
    'check-grace-period-expirations': {
        'task': 'workers.b2c_worker.tasks.check_grace_period_expirations',
        'schedule': crontab(hour=3, minute=0),
    },
}
