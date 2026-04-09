
import argparse
import asyncio
import uuid
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../")))

from modules.domains.b2b.bank_surveillance.tasks.alerting import _run_aggregation_standalone

DEMO_TENANT_ID = "b5e1fa40-89f4-50c2-a3f4-4c122000beef"

async def main():
    parser = argparse.ArgumentParser(description="Generate Incidents and Alerts from RiskEvents")
    parser.add_argument("--tenant-id", default=DEMO_TENANT_ID, help="Tenant UUID")
    parser.add_argument("--start-date", help="YYYY-MM-DD")
    parser.add_argument("--end-date", help="YYYY-MM-DD")
    
    args = parser.parse_args()
    
    print(f"🚀 Starting Incident Generation for Tenant: {args.tenant_id}")
    if args.start_date:
        print(f"📅 Date Range: {args.start_date} to {args.end_date or 'Now'}")
    
    result = await _run_aggregation_standalone(
        args.tenant_id,
        args.start_date,
        args.end_date
    )
    
    print("\n✅ Generation Complete!")
    print(f"   Events Processed: {result.get('events_processed', 0)}")
    print(f"   Incidents Created: {result.get('incidents_created', 0)}")
    print(f"   Alerts Created: {result.get('alerts_created', 0)}")
    
    # Auto-escalate a few cases for demo
    if args.tenant_id == DEMO_TENANT_ID:
        await auto_escalate_cases(args.tenant_id)
        print("\n✅ Demo Cases Created!")

async def auto_escalate_cases(tenant_id_str: str, limit: int = 3):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import select, func
    from core.config import settings
    from modules.domains.b2b.bank_surveillance.models.alert import Alert, AlertSeverity, AlertStatus
    from modules.domains.b2b.bank_surveillance.services.alert_service import alert_service
    
    tenant_id = uuid.UUID(tenant_id_str)
    
    db_url = settings.database_url
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(db_url)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as db:
        # Set RLS Context to ensure visibility
        from core.db.rls import rls_service
        await rls_service.set_tenant_context(db, tenant_id)
        
        # Debug: Count total alerts for this tenant
        total_stmt = select(func.count(Alert.id)).where(Alert.tenant_id == tenant_id)
        total_alerts = (await db.execute(total_stmt)).scalar() or 0
        print(f"   [DEBUG] Total Alerts in DB for tenant {tenant_id}: {total_alerts}")

        if total_alerts == 0:
            # Check if ANY alerts exist (debug tenant mismatch)
            any_alerts = await db.execute(select(func.count(Alert.id)))
            global_count = any_alerts.scalar() or 0
            if global_count > 0:
                print(f"   [WARN] Database has {global_count} alerts globally!")
                # Show distinct tenants
                distinct_tenants = await db.execute(select(Alert.tenant_id).distinct())
                print(f"   [DEBUG] Available Tenants with Alerts: {distinct_tenants.scalars().all()}")

        # Find Open Alerts (Any Severity)
        stmt = select(Alert).where(
            Alert.tenant_id == tenant_id,
            Alert.status == AlertStatus.OPEN.value
        ).limit(100)
        
        result = await db.execute(stmt)
        alerts = result.scalars().all()
        
        target_triggers = ["ljm", "raptor", "delete this"]
        escalated_count = 0
        
        print(f"   Scanning {len(alerts)} alerts for keywords {target_triggers}...")
        
        for i, alert in enumerate(alerts):
            if escalated_count >= limit:
                break
            
            md = alert.metadata_ or {}
            keywords = md.get("matched_keywords", [])
            
            # Check for keywords in ai_analysis as well (user feedback)
            ai_analysis = md.get("ai_analysis", {})
            if isinstance(ai_analysis, dict):
                ai_keywords = ai_analysis.get("keywords", [])
                if isinstance(ai_keywords, list):
                    keywords.extend(ai_keywords)
            
            # Deduplicate
            keywords = list(set(keywords))
            
            # Debug first alert
            if i == 0:
                print(f"   [DEBUG] Sample Meta: {md}")

            is_match = False
            for k in keywords:
                k_lower = k.lower()
                if any(t in k_lower for t in target_triggers):
                    is_match = True
                    break
            
            if is_match:
                await alert_service.escalate_alert(db, alert.id, tenant_id)
                print(f"     - Escalated Alert {str(alert.id)[:8]} (Keywords: {keywords}) -> Case")
                escalated_count += 1
        
        # Fallback if no specific keywords found
        if escalated_count == 0 and alerts:
            print("   ⚠️ No specific keyword matches found. Falling back to general escalation.")
            for alert in alerts[:limit]:
                await alert_service.escalate_alert(db, alert.id, tenant_id)
                print(f"     - [Fallback] Escalated Alert {str(alert.id)[:8]} -> Case")
            
        await db.commit()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
