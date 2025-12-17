
import os
import sys
import time

# Add /app to path
sys.path.append("/app")

# Ensure proper settings load
os.environ["TESTING"] = "0"
# Ensure we point to the RIGHT celery app
os.environ["CELERY_BROKER_URL"] = "redis://redis:6379/0"
os.environ["CELERY_RESULT_BACKEND"] = "redis://redis:6379/0"

from workers.b2b_worker.email_tasks import send_invitation_email
from workers.b2b_worker.celery_app import celery_app

def run_test():
    print("Testing Celery Dispatch...")
    print(f"App: {celery_app.main}")
    print(f"Broker: {celery_app.conf.broker_url}")
    
    # Send a dummy task
    # We use a random ID. The worker will likely fail to find it, 
    # BUT we should see the "Received task" in the worker logs.
    task = send_invitation_email.delay(
        invitation_id="00000000-0000-0000-0000-000000000000",
        tenant_id="00000000-0000-0000-0000-000000000000"
    )
    print(f"Task sent! ID: {task.id}")
    
if __name__ == "__main__":
    run_test()
