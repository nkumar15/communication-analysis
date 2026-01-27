import asyncio
import os
import sys
import uuid
import time
import random
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append("/home/neeraj/codes/enterprisesso/backend")

from modules.domains.b2b.bank_surveillance.models.alert import Alert
from core.config import settings

async def backfill_display_ids():
    print("Starting backfill for Alert display_ids...")
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Fetch alerts with missing display_id
        stmt = select(Alert).where(Alert.display_id.is_(None))
        result = await db.execute(stmt)
        alerts = result.scalars().all()
        
        print(f"Found {len(alerts)} alerts to update.")
        
        updated_count = 0
        for alert in alerts:
            ts = int(alert.detected_at.timestamp())
            suffix = random.randint(100, 999)
            # Ensure unique by adding a counter if needed, but random suffix is decent for now
            display_id = f"ALT-{ts}{suffix}"
            
            alert.display_id = display_id
            updated_count += 1
            print(f"  Updated {alert.id} -> {display_id}")
            
        await db.commit()
        print(f"Successfully backfilled {updated_count} alerts.")

if __name__ == "__main__":
    asyncio.run(backfill_display_ids())
