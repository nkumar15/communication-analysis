
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    print("Attempting to import workers.b2b_worker.audit_tasks...")
    from workers.b2b_worker.audit_tasks import persist_audit_log
    print("Import successful!")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
