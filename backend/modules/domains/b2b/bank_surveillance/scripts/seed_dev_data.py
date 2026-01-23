import asyncio
import random
import uuid
import sys
import argparse
import csv
import os
import yaml
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from core.config import settings
from modules.domains.b2b.bank_surveillance.models.communication import Communication
from modules.domains.b2b.bank_surveillance.models.alert import Alert, AlertStatus, AlertSeverity, RiskType
from modules.b2b.models.user import UserModel
from modules.b2b.models.tenant import TenantModel
from core.db.rls import rls_service

# Service Layer Imports
from modules.domains.b2b.bank_surveillance.services.alert_service import alert_service
from modules.domains.b2b.bank_surveillance.services.ingestion import CommunicationIngestionService, EmailParsedData
from modules.domains.b2b.bank_surveillance.services.regulatory_service import regulatory_service
from modules.domains.b2b.bank_surveillance.services.control_service import control_service
from modules.domains.b2b.bank_surveillance.schemas.alert import AlertCreate
from modules.domains.b2b.bank_surveillance.schemas.regulatory import RegulatoryDocumentCreate
from modules.domains.b2b.bank_surveillance.schemas.control import SurveillanceControlCreate

# Configure DB
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(db_url)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

DATA_REGION='US'
SENSITIVITY_LEVEL_ID='1'

def parse_csv_date(date_str: str) -> datetime:
    try:
        # parsedate_to_datetime parses email standard date header format (RFC 2822)
        # e.g., "Tue, 30 Oct 2001 05:17:09 -0800"
        return parsedate_to_datetime(date_str)
    except Exception:
        # Fallback to current time if parsing fails
        return datetime.now(timezone.utc)

async def seed_meta(db: AsyncSession, tenant_id: uuid.UUID):
    """
    Seeds meta data (regulatory library and controls) for a given tenant.
    Reuses logic from seed_use_case_meta.py but integrated here.
    """
    print(f"🌱 Seeding meta data (Regulatory & Controls) for tenant: {tenant_id}")
    
    # Paths relative to this script
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../scripts/b2b/use_cases/bank_surveillance"))
    
    # 1. Load Regulatory Documents
    reg_path = os.path.join(base_path, "regulatory_library.yaml")
    if os.path.exists(reg_path):
        with open(reg_path, "r") as f:
            reg_data = yaml.safe_load(f)
            
        doc_map = {} # title -> id
        for doc in reg_data.get("regulatory_documents", []):
            existing_docs = await regulatory_service.list_documents(db, tenant_id, limit=100)
            existing = next((d for d in existing_docs if d.title == doc["title"]), None)
            
            if existing:
                doc_map[doc["title"]] = existing.id
                continue

            print(f"   Creating document: {doc['title']}")
            doc_in = RegulatoryDocumentCreate(
                tenant_id=tenant_id,
                title=doc["title"],
                framework=doc.get("framework"),
                year=doc.get("year"),
                version=doc.get("version"),
                storage_path=doc.get("storage_path")
            )
            db_doc = await regulatory_service.create_document(db, doc_in)
            doc_map[doc["title"]] = db_doc.id

        # 2. Load Surveillance Controls
        ctrl_path = os.path.join(base_path, "surveillance_controls.yaml")
        if os.path.exists(ctrl_path):
            with open(ctrl_path, "r") as f:
                ctrl_data = yaml.safe_load(f)

            for ctrl in ctrl_data.get("surveillance_controls", []):
                existing_ctrls = await control_service.list_controls(db, tenant_id, limit=100)
                existing = next((c for c in existing_ctrls if c.risk_indicator == ctrl["risk_indicator"]), None)
                
                if existing:
                    continue

                print(f"   Creating control: {ctrl['risk_indicator']}")
                reg_id = doc_map.get(ctrl.get("regulatory_reference"))
                
                ctrl_in = SurveillanceControlCreate(
                    tenant_id=tenant_id,
                    risk_typology=ctrl["risk_typology"],
                    risk_indicator=ctrl["risk_indicator"],
                    regulatory_id=reg_id,
                    regulatory_reference_text=ctrl.get("regulatory_reference"),
                    detection_methods=ctrl.get("detection_methods", []),
                    status=ctrl.get("status", "Active")
                )
                await control_service.create_control(db, ctrl_in)
    else:
        print(f"⚠️ Meta YAMLs not found at {base_path}. Skipping meta seed.")

async def seed_communications(db: AsyncSession, tenant_id: uuid.UUID, target_count: int = 50, csv_path: str = None) -> List[Communication]:
    """
    Seeds communications for a given tenant.
    If csv_path is provided, ingests from CSV. Otherwise generates dummy data.
    """
    print("🔍 Checking for communications...")
    count_res = await db.execute(select(func.count(Communication.id)).where(Communication.tenant_id == tenant_id))
    comm_count = count_res.scalar()
    
    # If using CSV, we might want to append even if data exists, but for now let's stick to the check
    # to avoid double insertion if run twice. However, if CSV is strictly requested, we should probably check duplications differently.
    # For simplicity, if csv_path is present, we try to ingest unique message_ids.
    
    ingestion_service = CommunicationIngestionService(db)
    new_comms_count = 0
    
    if csv_path:
        print(f"📂 Ingesting from CSV: {csv_path}")
        try:
            with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                print(f"   found {len(rows)} rows in CSV.")
                
                for row in rows:
                    if new_comms_count >= target_count and target_count > 0:
                        break
                        
                    msg_id_str = row.get('message_id', '').strip()
                    if not msg_id_str:
                        continue
                    
                    email_data = EmailParsedData(
                        message_id=msg_id_str,
                        sender=row.get('sender', 'unknown@example.com'),
                        recipients=[r.strip() for r in row.get('recipients', '').split(',') if r.strip()],
                        subject=row.get('subject', 'No Subject'),
                        body=row.get('body', ''),
                        date=parse_csv_date(row.get('date', ''))
                    )
                    
                    success = await ingestion_service.ingest_message(email_data, tenant_id)
                    if success:
                        new_comms_count += 1

            await db.commit()
            print(f"✅ Ingested {new_comms_count} communications from CSV.")

        except FileNotFoundError:
            print(f"❌ CSV file not found: {csv_path}")
        except Exception as e:
             print(f"❌ Error reading/ingesting CSV: {e}")
             
    else:
        # Fallback to dummy generation if no CSV
        if comm_count >= target_count:
            print(f"✅ Found {comm_count} communications. Skipping generation.")
        else:
            print(f"⚠️ Only {comm_count} communications found. Generating up to {target_count} dummy communications...")
            
            subjects = [
                "Lunch meeting", "Project Update", "Confidential: Merger", "Stock tips", 
                "Golf this weekend?", "Quarterly Report", "Urgent: Wire Transfer", "Suspicious Activity"
            ]
            
            needed = target_count - comm_count
            
            for i in range(needed):
                email_data = EmailParsedData(
                    message_id=f"msg_{uuid.uuid4().hex[:12]}",
                    sender=f"trader{random.randint(1,10)}@example.com",
                    recipients=[f"client{random.randint(1,5)}@external.com"],
                    subject=random.choice(subjects),
                    body=f"This is a dummy message processing transaction #{random.randint(1000,9999)}. {'Use signal app' if random.random() > 0.8 else 'Standard procedure'}.",
                    date=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 60))
                )
                await ingestion_service.ingest_message(email_data, tenant_id)
                new_comms_count += 1
            
            await db.commit()
            print(f"✅ Created {new_comms_count} dummy communications.")
    
    # Return all communications (existing + new) for alerts
    # We fetch only relevant ones or up to limit for alerts
    limit = target_count if target_count > 0 else 50
    print(f"   ℹ️ Fetching up to {limit} communications for alert generation...")
    stmt = select(Communication).where(Communication.tenant_id == tenant_id).order_by(Communication.timestamp.desc()).limit(limit)
    all_comms_res = await db.execute(stmt)
    all_comms = all_comms_res.scalars().all()
    print(f"   ℹ️ Fetched {len(all_comms)} communications.")
    return all_comms

async def seed_alerts(db: AsyncSession, tenant_id: uuid.UUID, user_ids: List[uuid.UUID], communications: List[Communication], min_alerts: int = 15):
    """
    Seeds alerts for a given tenant, linking them to existing communications.
    """
    print("🔍 checking for alerts...")
    
    if not communications:
        print("⚠️ No communications provided to create alerts for.")
        return

    print(f"   ℹ️ Found {len(communications)} communications available for alerting.")
    
    count_alerts_res = await db.execute(select(func.count(Alert.id)).where(Alert.tenant_id == tenant_id))
    alert_count = count_alerts_res.scalar()
    
    if alert_count >= min_alerts:
        print(f"✅ Found {alert_count} alerts. Skipping generation.")
        return

    print("⚠️ Low alert count. Generating alerts using alert_service...")
    created_count = 0
    
    for comm in communications:
        # Force creation for first N, then random
        if created_count >= min_alerts:
            break
            
        risk_type = random.choice(list(RiskType))
        severity = random.choice(list(AlertSeverity))
        status = random.choice(list(AlertStatus))
        assigned_to = random.choice(user_ids) if user_ids and random.random() > 0.3 else None
        
        alert_in = AlertCreate(
            tenant_id=tenant_id,
            communication_id=comm.id,
            risk_type=risk_type,
            severity=severity,
            status=status,
            assigned_to=assigned_to,
            description=f"Generated alert for {risk_type.value}",
            metadata={"confidence": 0.85, "model": "dev-seed"},
            detected_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))
        )
        await alert_service.create_alert(db, alert_in)
        created_count += 1
    
    await db.commit()
    print(f"✅ Created {created_count} alerts.")

async def seed_dev_data(target_tenant_id: str = None, csv_path: str = None):
    print("🚀 Starting Bank Surveillance Seeding (Refactored)...")
    
    async with SessionLocal() as db:
        # Platform Admin Context for global seeding
        await rls_service.set_platform_admin_context(db)
        
        tenant_id = None
        
        if target_tenant_id:
            try:
                tenant_uuid = uuid.UUID(target_tenant_id)
                result = await db.execute(select(TenantModel).where(TenantModel.id == tenant_uuid))
                tenant = result.scalar_one_or_none()
                if not tenant:
                    print(f"❌ Tenant with ID {target_tenant_id} not found.")
                    return
                tenant_id = tenant.id
            except ValueError:
                print(f"❌ Invalid UUID provided: {target_tenant_id}")
                return
        else:
            # Fallback: Pick the first available tenant if none provided (useful for dev)
            print("⚠️ No tenant ID provided. Fetching first available tenant...")
            result = await db.execute(select(TenantModel).limit(1))
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                print("❌ No tenants found in database. Please seed tenants first.")
                return
            
            tenant_id = tenant.id
        
        if not tenant_id:
            print("❌ No tenant found to seed.")
            return

        print(f"✅ Target Tenant: {tenant.name} ({tenant_id})")

        # 1. Seed Meta Data
        await seed_meta(db, tenant_id)

        # 2. Fetch users
        print("🔍 Fetching existing users for assignment...")
        users_result = await db.execute(select(UserModel).where(UserModel.tenant_id == tenant_id))
        users = users_result.scalars().all()
        
        user_ids = [u.id for u in users]
        if not user_ids:
            print("⚠️ No users found in this tenant. Alerts will be unassigned.")
        else:
            print(f"✅ Found {len(users)} users to assign alerts to.")

        # 3. Seed Communications (from CSV if provided)
        # Increase target_count if using CSV to process more rows (default 50 might be too small for real dump)
        target = 1000 if csv_path else 50
        communications = await seed_communications(db, tenant_id, target_count=target, csv_path=csv_path)

        # 4. Seed Alerts
        await seed_alerts(db, tenant_id, user_ids, communications)

    print("\n🏁 Seeding Complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Bank Surveillance Data")
    parser.add_argument("--tenant-id", type=str, help="UUID of the tenant to seed data for", default=None)
    parser.add_argument("--csv-path", type=str, help="Absolute path to CSV file for ingesting communications", default=None)
    
    args = parser.parse_args()
    
    asyncio.run(seed_dev_data(args.tenant_id, args.csv_path))
