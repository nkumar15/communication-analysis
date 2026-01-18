
import sys
import os

print("Testing imports and delay execution...")
try:
    # Set necessary env vars for config to load if needed (though docker env has them)
    # from core.config import settings 
    # print(f"Broker: {settings.celery_broker_url_resolved}")

    from workers.b2b_worker.audit_tasks import persist_audit_log
    print("Importing audit_tasks success")
    
    # Try to call delay
    print("Calling persist_audit_log.delay()...")
    # minimal dummy data
    dummy_data = {
        'tenant_id': '00000000-0000-0000-0000-000000000000',
        'event_type': 'test',
        'actor_id': '00000000-0000-0000-0000-000000000000',
        'resource_id': '00000000-0000-0000-0000-000000000000'
    }
    res = persist_audit_log.delay(dummy_data)
    print(f"Delay called. Result ID: {res.id}")
    
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
