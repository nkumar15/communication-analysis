"""
Seed script for Platform Foundation.
Creates:
1. Platform Tenant (singleton)
2. Platform Roles (platform_admin, support_staff, billing_manager)

This is for the NEW separated platform system.

Usage:
    python scripts/seed_system_tenant.py --firebase-tenant-id your-platform-tenant-id
    python scripts/seed_system_tenant.py --firebase-tenant-id platform-abc123 --oidc-provider oidc.okta
"""
import asyncio
import argparse
import os
import sys
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.platform.models import PlatformTenant, PlatformRole
from core.config import settings

async def seed_platform_system(
    firebase_tenant_id: str = "platform-tenant",
    oidc_provider_id: str = "platform-oidc",
    platform_name: str = "SaaS Platform",
    email_domain: str = "platform.local"
):
    print("🌱 Seeding Platform Foundation...")
    print(f"   Firebase Tenant ID: {firebase_tenant_id}")
    print(f"   OIDC Provider ID: {oidc_provider_id}")
    print(f"   Platform Name: {platform_name}")
    
    db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. Check/Create Platform Tenant (singleton)
        result = await db.execute(select(PlatformTenant))
        platform_tenant = result.scalar_one_or_none()
        
        if not platform_tenant:
            print("✨ Creating Platform Tenant...")
            platform_tenant = PlatformTenant(
                name=platform_name,
                firebase_tenant_id=firebase_tenant_id,
                oidc_provider_id=oidc_provider_id,
                email_domain=email_domain
            )
            db.add(platform_tenant)
            await db.commit()
            await db.refresh(platform_tenant)
            print(f"   ✅ Platform Tenant created: {platform_tenant.name}")
        else:
            print(f"   ℹ️  Platform Tenant already exists: {platform_tenant.name}")
        
        # 2. Create Platform Roles
        role_definitions = [
            {
                "name": "platform_admin",
                "display_name": "Platform Administrator",
                "description": "Full access to platform management and configuration",
                "is_system_role": True
            },
            {
                "name": "support_staff",
                "display_name": "Support Staff",
                "description": "Customer support and troubleshooting access",
                "is_system_role": True
            },
            {
                "name": "billing_manager",
                "display_name": "Billing Manager",
                "description": "Billing, subscriptions, and payment management",
                "is_system_role": True
            }
        ]
        
        print("\n📋 Creating Platform Roles...")
        created_count = 0
        
        for role_def in role_definitions:
            result = await db.execute(
                select(PlatformRole).where(PlatformRole.name == role_def["name"])
            )
            existing_role = result.scalar_one_or_none()
            
            if not existing_role:
                new_role = PlatformRole(
                    platform_tenant_id=platform_tenant.id,
                    **role_def
                )
                db.add(new_role)
                created_count += 1
                print(f"   ✅ Created role: {role_def['display_name']}")
            else:
                print(f"   ℹ️  Role already exists: {role_def['display_name']}")
        
        if created_count > 0:
            await db.commit()
        
        print(f"\n✅ Platform foundation setup complete!")
        print(f"   Platform Tenant ID: {platform_tenant.id}")
        print(f"   Firebase Tenant ID: {platform_tenant.firebase_tenant_id}")
        
        # Return platform tenant ID for use by other scripts
        return str(platform_tenant.id)

def main():
    parser = argparse.ArgumentParser(
        description="Seed Platform Foundation (separate from customer tenants)"
    )
    parser.add_argument(
        "--firebase-tenant-id",
        help="Firebase Tenant ID for platform (from GCIP)"
    )
    parser.add_argument(
        "--oidc-provider",
        help="OIDC Provider ID"
    )
    parser.add_argument(
        "--name",
        default="SaaS Platform",
        help="Platform display name"
    )
    parser.add_argument(
        "--domain",
        default="platform.local",
        help="Platform email domain"
    )
    
    args = parser.parse_args()
    
    # Interactive mode
    firebase_tenant_id = args.firebase_tenant_id
    oidc_provider = args.oidc_provider
    name = args.name
    domain = args.domain
    
    if not firebase_tenant_id:
        print("🌱 Enter Platform Tenant Details:")
        firebase_tenant_id = input("   Firebase Tenant ID [platform-system]: ").strip() or "platform-system"
        
        oidc_input = input("   OIDC Provider ID [platform-oidc]: ").strip()
        if oidc_input:
            oidc_provider = oidc_input
        else:
            oidc_provider = "platform-oidc"
            
        name_input = input("   Platform Name [SaaS Platform]: ").strip()
        if name_input:
            name = name_input
            
        domain_input = input("   Email Domain [platform.local]: ").strip()
        if domain_input:
            domain = domain_input
    
    # Ensure defaults if non-interactive but args missing
    if not oidc_provider:
        oidc_provider = "platform-oidc"

    asyncio.run(seed_platform_system(
        firebase_tenant_id=firebase_tenant_id,
        oidc_provider_id=oidc_provider,
        platform_name=name,
        email_domain=domain
    ))

if __name__ == "__main__":
    main()
