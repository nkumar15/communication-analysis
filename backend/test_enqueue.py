from celery import Celery
from core.config import settings
import sys

# Force early resolve
print(f"Broker URL: {settings.celery_broker_url_resolved}")

app = Celery('test', broker=settings.celery_broker_url_resolved)
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json', 
)

payload = {
    "tenant_id": "05b51fa4-45f4-50c2-b3f4-4c122000347b",
    "file_path": "test_path",
    "job_id": "manual_test",
    "document_metadata": {}
}

print("Sending task...")
try:
    res = app.send_task('domain.ingest_document', args=[payload])
    print(f"Sent task ID: {res.id}")
except Exception as e:
    print(f"Error sending task: {e}")
