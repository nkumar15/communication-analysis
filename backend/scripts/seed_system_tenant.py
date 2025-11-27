"""
Seed script for SaaS Admin Console foundation.
Creates:
1. System Tenant (if not exists)
2. Platform Admin Role (if not exists)

Usage:
    python scripts/seed_system_tenant.py --firebase-tenant-id your-tenant-id
    python scripts/seed_system_tenant.py --firebase-tenant-id demo-abc123 --oidc-provider oidc.okta
"""
import asyncio
import argparse
import os
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db_models import TenantModel, Base
from app.rbac_models import Role
from app.constants import RoleName
from app.config import settings

async def seed_system_tenant(
    firebase_tenant_id: str = "system-platform",
    oidc_provider_id: str = "system-oidc",
    tenant_name: str = "SaaS Platform System",
    tenant_domain: str = "system.local"
):
    print("🌱 Seeding SaaS Admin Foundation...")
    print(f"   Firebase Tenant ID: {firebase_tenant_id}")
    print(f"   OIDC Provider ID: {oidc_provider_id}")
    
    db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. Check/Create System Tenant
        result = await db.execute(
            select(TenantModel).where(TenantModel.firebase_tenant_id == firebase_tenant_id)
        )
        system_tenant = result.scalar_one_or_none()
        
        if not system_tenant:
            print("Creating System Tenant...")
            system_tenant = TenantModel(
                name=tenant_name,
                domain=tenant_domain,
                firebase_tenant_id=firebase_tenant_id,
                oidc_provider_id=oidc_provider_id,
                is_active=True,
                activation_status='active',
                is_system_tenant=True
            )
            db.add(system_tenant)
            await db.commit()
            await db.refresh(system_tenant)
            print(f"✅ System Tenant created: {system_tenant.id}")
        else:
            print(f"ℹ️ System Tenant already exists: {system_tenant.id}")
            
        # 2. Check/Create Platform Admin Role
        result = await db.execute(
            select(Role)
            .where(Role.tenant_id == system_tenant.id)
            .where(Role.name == RoleName.PLATFORM_ADMIN)
        )
        admin_role = result.scalar_one_or_none()
        
        if not admin_role:
            print("Creating Platform Admin Role...")
            admin_role = Role(
                tenant_id=system_tenant.id,
                name=RoleName.PLATFORM_ADMIN,
                display_name="Platform Administrator",
                description="Full access to SaaS Admin Console",
                is_system_role=True
            )
            db.add(admin_role)
            await db.commit()
            print("✅ Platform Admin Role created")
        else:
            print("ℹ️ Platform Admin Role already exists")
            
    await engine.dispose()
    print("✨ Seeding complete!")

def main():
    parser = argparse.ArgumentParser(
        description='Seed System Tenant and Platform Admin Role for SaaS Admin Console',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Use default values (system-platform)
  python scripts/seed_system_tenant.py

  # Specify your Firebase tenant ID
  python scripts/seed_system_tenant.py --firebase-tenant-id demo-abc123

  # Full customization
  python scripts/seed_system_tenant.py \\
    --firebase-tenant-id demo-abc123 \\
    --oidc-provider oidc.okta \\
    --name "My Platform Admin" \\
    --domain platform.mycompany.com
        '''
    )
    
    parser.add_argument(
        '--firebase-tenant-id',
        default='system-platform',
        help='Firebase tenant ID from GCIP (default: system-platform)'
    )
    parser.add_argument(
        '--oidc-provider',
        default='system-oidc',
        help='OIDC provider ID configured in Firebase (default: system-oidc)'
    )
    parser.add_argument(
        '--name',
        default='SaaS Platform System',
        help='Display name for the system tenant (default: SaaS Platform System)'
    )
    parser.add_argument(
        '--domain',
        default='system.local',
        help='Domain for the system tenant (default: system.local)'
    )
    
    args = parser.parse_args()
    
    # Run seeding
    asyncio.run(seed_system_tenant(
        firebase_tenant_id=args.firebase_tenant_id,
        oidc_provider_id=args.oidc_provider,
        tenant_name=args.name,
        tenant_domain=args.domain
    ))

if __name__ == "__main__":
    main()
