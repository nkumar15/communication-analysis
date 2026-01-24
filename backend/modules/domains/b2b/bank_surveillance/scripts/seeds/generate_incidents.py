
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

if __name__ == "__main__":
    asyncio.run(main())
