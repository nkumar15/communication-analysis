#!/usr/bin/env python3
"""
Create Platform Admin User

This script creates a platform admin user in Firebase and the platform_users table.
Works with the NEW separated platform system (platform_users, not users table).

Usage:
    python scripts/create_platform_admin.py --email admin@yourcompany.com
    python scripts/create_platform_admin.py --email admin@yourcompany.com --name "John Doe"
"""
import asyncio
import argparse
import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.platform.models import PlatformTenant, PlatformRole, PlatformUser
from core.config import settings
from core.firebase.auth_service import firebase_auth_service
import firebase_admin
from firebase_admin import auth, tenant_mgt

async def create_platform_admin(email: str, name: str = None, role_name: str = "platform_admin"):
    """
    Create a platform admin user in the platform system.
    
    Args:
        email: Email address for the platform user
        name: Display name (defaults to email username)
        role_name: Platform role (default: platform_admin)
    """
    print(f"🔧 Creating Platform User: {email}")
    print(f"   Role: {role_name}")
    
    # Initialize Firebase
    firebase_auth_service.initialize()
    
    # Setup database connection
    db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. Find Platform Tenant (singleton)
        result = await db.execute(select(PlatformTenant))
        platform_tenant = result.scalar_one_or_none()
        
        if not platform_tenant:
            print("❌ Platform tenant not found!")
            print("   Run: python scripts/seed_system_tenant.py first")
            return
        
        print(f"✅ Found platform tenant: {platform_tenant.name}")
        print(f"   Firebase Tenant ID: {platform_tenant.firebase_tenant_id}")
        
        # 2. Find Platform Role
        result = await db.execute(
            select(PlatformRole)
            .where(PlatformRole.platform_tenant_id == platform_tenant.id)
            .where(PlatformRole.name == role_name)
        )
        platform_role = result.scalar_one_or_none()
        
        if not platform_role:
            print(f"❌ Platform role '{role_name}' not found!")
            print("   Available roles should be seeded by seed_system_tenant.py")
            return
        
        print(f"✅ Found platform role: {platform_role.display_name}")
        
        # 3. Check if user already exists in platform_users
        result = await db.execute(
            select(PlatformUser).where(PlatformUser.email == email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"⚠️  Platform user already exists: {existing_user.display_name or existing_user.email}")
            print(f"   Firebase UID: {existing_user.firebase_uid}")
            return
        
        # 4. Create Firebase user in platform tenant
        print(f"\n🔥 Creating Firebase user in platform tenant...")
        print(f"   Tenant ID: {platform_tenant.firebase_tenant_id}")
        
        try:
            # Get tenant-scoped Firebase Auth client
            tenant_auth = tenant_mgt.auth_for_tenant(platform_tenant.firebase_tenant_id)
            
            # Check if Firebase user exists
            try:
                existing_firebase_user = tenant_auth.get_user_by_email(email)
                firebase_uid = existing_firebase_user.uid
                print(f"✅ Firebase user already exists: {firebase_uid}")
            except auth.UserNotFoundError:
                # Create new Firebase user
                firebase_user = tenant_auth.create_user(
                    email=email,
                    display_name=name or email.split('@')[0],
                    email_verified=True  # Platform users are pre-verified
                )
                firebase_uid = firebase_user.uid
                print(f"✅ Created Firebase user: {firebase_uid}")
        
        except Exception as e:
            print(f"❌ Error creating Firebase user: {e}")
            print(f"   Make sure Firebase tenant '{platform_tenant.firebase_tenant_id}' exists in GCIP")
            return
        
        # 5. Create platform user in database
        print(f"\n💾 Creating platform user in database...")
        
        platform_user = PlatformUser(
            platform_tenant_id=platform_tenant.id,
            platform_role_id=platform_role.id,
            email=email,
            firebase_uid=firebase_uid,
            display_name=name or email.split('@')[0]
        )
        
        db.add(platform_user)
        await db.commit()
        await db.refresh(platform_user)
        
        print(f"✅ Platform user created successfully!")
        print(f"\n📋 User Details:")
        print(f"   ID: {platform_user.id}")
        print(f"   Email: {platform_user.email}")
        print(f"   Name: {platform_user.display_name}")
        print(f"   Role: {platform_role.display_name}")
        print(f"   Firebase UID: {platform_user.firebase_uid}")
        
        print(f"\n🔐 Login Instructions:")
        print(f"   1. Go to: http://localhost:3000/platform-login")
        print(f"   2. Login with: {email}")
        print(f"   3. Use your OIDC provider configured in Firebase")
        
        return str(platform_user.id)

def main():
    parser = argparse.ArgumentParser(
        description="Create Platform Admin User (in separated platform system)"
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email address for the platform user"
    )
    parser.add_argument(
        "--name",
        help="Display name (defaults to email username)"
    )
    parser.add_argument(
        "--role",
        default="platform_admin",
        help="Platform role (default: platform_admin)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(create_platform_admin(
        email=args.email,
        name=args.name,
        role_name=args.role
    ))

if __name__ == "__main__":
    main()
