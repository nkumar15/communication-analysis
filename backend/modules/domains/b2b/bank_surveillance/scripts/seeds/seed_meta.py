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
from modules.b2b.models.geographic_region import GeographicRegion
from modules.b2b.models.sensitivity_level import SensitivityLevel
from modules.domains.b2b.bank_surveillance.services.regulatory_service import regulatory_service
from modules.domains.b2b.bank_surveillance.services.policy import policy_rag_service
from modules.domains.b2b.bank_surveillance.services.control_service import control_service
from modules.domains.b2b.bank_surveillance.schemas.regulatory import RegulatoryDocumentCreate
from modules.domains.b2b.bank_surveillance.schemas.control import SurveillanceControlCreate
from modules.domains.b2b.bank_surveillance.models import IngestionConfigTemplate, IngestionConfig
from core.db.rls import rls_service

# DB Connection
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(db_url)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed_ingestion_config_templates(db: AsyncSession):
    """
    Seeds global ingestion config templates from YAML.
    These are shared across all tenants (not tenant-specific).
    """
    print("🌱 Seeding ingestion config templates (global)...")
    
    yaml_path = os.path.join(os.path.dirname(__file__), "ingestion_config_template.yaml")
    if not os.path.exists(yaml_path):
        print(f"⚠️ Ingestion config template YAML not found at {yaml_path}")
        return
    
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
    
    for template in data.get("ingestion_config_templates", []):
        # Check if exists by name
        existing = await db.execute(
            select(IngestionConfigTemplate).where(IngestionConfigTemplate.name == template["name"])
        )
        if existing.scalar_one_or_none():
            print(f"   ℹ️ Template '{template['name']}' already exists. Skipping.")
            continue
        
        print(f"   Creating template: {template['name']}")
        db.add(IngestionConfigTemplate(
            name=template["name"],
            description=template.get("description"),
            is_default=template.get("is_default", False),
            region_strategy=template.get("region_strategy", "default"),
            sender_domain_map=template.get("sender_domain_map", {}),
            classification_strategy=template.get("classification_strategy", "default"),
            channel_map=template.get("channel_map", {}),
            content_rules=template.get("content_rules", []),
        ))
    
    print("✅ Ingestion config templates seeded.")


async def clone_ingestion_config_for_tenant(db: AsyncSession, tenant_id: uuid.UUID):
    """
    Clones ingestion config from default template for a tenant.
    Called during tenant onboarding.
    """
    # Check if tenant already has config
    existing = await db.execute(
        select(IngestionConfig).where(IngestionConfig.tenant_id == tenant_id)
    )
    if existing.scalar_one_or_none():
        print(f"   ℹ️ Tenant {tenant_id} already has ingestion config. Skipping.")
        return
    
    # Get default template
    template_result = await db.execute(
        select(IngestionConfigTemplate).where(IngestionConfigTemplate.is_default == True)
    )
    template = template_result.scalar_one_or_none()
    
    if not template:
        print("   ⚠️ No default template found. Creating minimal config.")
        template = IngestionConfigTemplate(name="default", is_default=True)
    
    # Get tenant's first region (for default_region_id)
    region_result = await db.execute(
        select(GeographicRegion).limit(1)
    )
    first_region = region_result.scalar_one_or_none()
    
    # Get "Internal" sensitivity level (for default_level_id)
    level_result = await db.execute(
        select(SensitivityLevel).where(SensitivityLevel.name == "Internal")
    )
    internal_level = level_result.scalar_one_or_none()
    
    # Clone config
    config = IngestionConfig(
        tenant_id=tenant_id,
        template_id=template.id if template.id else None,
        region_strategy=template.region_strategy,
        default_region_id=first_region.id if first_region else None,
        sender_domain_map=template.sender_domain_map or {},
        classification_strategy=template.classification_strategy,
        default_level_id=internal_level.id if internal_level else None,
        channel_map=template.channel_map or {},
        content_rules=template.content_rules or [],
    )
    db.add(config)
    print(f"   ✅ Created ingestion config for tenant {tenant_id}")


async def seed_meta(db: AsyncSession, tenant_id: uuid.UUID):
    """
    Seeds meta data (regulatory library, controls, and ingestion config) for a given tenant.
    """
    # 0. Seed global templates first (idempotent)
    await seed_ingestion_config_templates(db)
    
    # Set Tenant Context for RLS (Switch from Platform Admin to Tenant Scope)
    await rls_service.set_tenant_context(db, tenant_id)
    
    # 0.5 Clone ingestion config for tenant
    await clone_ingestion_config_for_tenant(db, tenant_id)
    
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

        # --- RAG Indexing ---
        if doc.get("text_content"):
            print(f"   Indexing content for: {doc['title']}")
            await policy_rag_service.index_text(
                text=doc["text_content"],
                metadata={
                    "filename": doc["title"],
                    "framework": doc.get("framework"),
                    "tenant_id": str(tenant_id)
                },
                doc_id=str(db_doc.id)
            )

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
