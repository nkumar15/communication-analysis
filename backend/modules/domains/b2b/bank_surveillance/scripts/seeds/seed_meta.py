import asyncio
import yaml
import uuid
import sys
import os
import argparse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Setup path to import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../")))

from core.config import settings
from modules.b2b.models.tenant import TenantModel
from modules.domains.b2b.bank_surveillance.services.regulatory_service import regulatory_service
from modules.domains.b2b.bank_surveillance.services.control_service import control_service
from modules.domains.b2b.bank_surveillance.schemas.regulatory import RegulatoryDocumentCreate
from modules.domains.b2b.bank_surveillance.schemas.control import SurveillanceControlCreate
from core.db.rls import rls_service

# DB Connection
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(db_url)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def seed_meta(db: AsyncSession, tenant_id: uuid.UUID):
    """
    Seeds meta data (regulatory library and controls) for a given tenant.
    """
    print(f"🌱 Seeding meta data for tenant: {tenant_id}")
    
    # 1. Load Regulatory Documents
    reg_path = os.path.join(os.path.dirname(__file__), "regulatory_library.yaml")
    if not os.path.exists(reg_path):
        print(f"⚠️ Regulatory library YAML not found at {reg_path}")
        return

    with open(reg_path, "r") as f:
        reg_data = yaml.safe_load(f)
        
    doc_map = {} # title -> id
    for doc in reg_data.get("regulatory_documents", []):
        # Check if already exists to avoid duplicates
        existing_docs = await regulatory_service.list_documents(db, tenant_id, limit=100)
        existing = next((d for d in existing_docs if d.title == doc["title"]), None)
        
        if existing:
            print(f"   ℹ️ Document '{doc['title']}' already exists. Skipping.")
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
    ctrl_path = os.path.join(os.path.dirname(__file__), "surveillance_controls.yaml")
    if not os.path.exists(ctrl_path):
        print(f"⚠️ Surveillance controls YAML not found at {ctrl_path}")
        return

    with open(ctrl_path, "r") as f:
        ctrl_data = yaml.safe_load(f)

    for ctrl in ctrl_data.get("surveillance_controls", []):
        # Check if already exists
        existing_ctrls = await control_service.list_controls(db, tenant_id, limit=100)
        existing = next((c for c in existing_ctrls if c.risk_indicator == ctrl["risk_indicator"]), None)
        
        if existing:
            print(f"   ℹ️ Control '{ctrl['risk_indicator']}' already exists. Skipping.")
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

    await db.commit()
    print("✅ Meta seeding complete.")

async def run_standalone(tenant_id_str: str = None):
    async with SessionLocal() as db:
        await rls_service.set_platform_admin_context(db)
        
        if tenant_id_str:
            tenant_id = uuid.UUID(tenant_id_str)
        else:
            result = await db.execute(select(TenantModel).limit(1))
            tenant = result.scalar_one_or_none()
            if not tenant:
                print("❌ No tenants found.")
                return
            tenant_id = tenant.id
            
        await seed_meta(db, tenant_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Bank Surveillance Meta Data")
    parser.add_argument("--tenant-id", type=str, help="UUID of the tenant to seed data for", default=None)
    
    args = parser.parse_args()
    asyncio.run(run_standalone(args.tenant_id))
