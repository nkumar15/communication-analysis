
import sys
import os

print("Testing email task delay...")
try:
    from workers.b2b_worker.email_tasks import send_invitation_email
    print("Importing email_tasks success")
    
    print("Calling send_invitation_email.delay()...")
    res = send_invitation_email.delay(
        invitation_id='00000000-0000-0000-0000-000000000000',
        tenant_id='00000000-0000-0000-0000-000000000000'
    )
    print(f"Delay called. Result ID: {res.id}")
    
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
