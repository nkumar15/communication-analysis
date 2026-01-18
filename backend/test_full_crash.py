
import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from core.config import settings
from modules.b2b.services.invitation_service import invitation_service
from modules.b2b.services.tenant_service import tenant_service
from modules.b2b.models import UserModel, TenantModel
from sqlalchemy import select
from core.db.rls import rls_service

async def test_crash():
    print("Setting up DB...")
    db_url = settings.database_url
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://")
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        
    engine = create_async_engine(db_url)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as db:
        print("Fetching a tenant...")
        # Get a real tenant
        result = await db.execute(select(TenantModel).limit(1))
        tenant = result.scalar_one_or_none()
        if not tenant:
            print("No tenant found.")
            return

        print(f"Tenant: {tenant.name}, Domain: {tenant.domain}")
        
        # Get a user for this tenant
        result = await db.execute(select(UserModel).where(UserModel.tenant_id == tenant.id).limit(1))
        user = result.scalar_one_or_none()
        inviter_id = user.id if user else None
        
        email_to_invite = f"crash_test_999@{tenant.domain}"
        print(f"Inviting {email_to_invite}...")
        
        print("Setting RLS context (Platform Admin)...")
        await rls_service.set_platform_admin_context(db)

        print("Calling invite_user_to_tenant...")
        try:
            invitation, token = await invitation_service.invite_user_to_tenant(
                db=db,
                tenant_id=tenant.id,
                email=email_to_invite,
                role="member",
                invited_by_user_id=inviter_id,
                current_user_role="owner" 
            )
            print(f"Invitation created! ID: {invitation.id}")
            
            # Commit logic
            await db.commit()
            print("Committed.")
            
        except Exception as e:
            print(f"Service call failed: {e}")
            import traceback
            traceback.print_exc()
            
        print("Checking imports of tasks...")
        from workers.b2b_worker.audit_tasks import persist_audit_log
        print("Imported audit_tasks")
        
        print("Triggering delay...")
        res = persist_audit_log.delay({'event_type': 'crash_test'})
        print(f"Delay triggered. ID: {res.id}")

if __name__ == "__main__":
    # Fix for 'Task attached to a different loop'
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_crash())
