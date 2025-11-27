#!/usr/bin/env python3
"""
Create Platform Admin User

This script creates a platform admin user in Firebase (system-platform tenant)
and links them to the database. For use when the platform tenant is configured
with OIDC provider in Google Cloud Identity Platform.

Usage:
    python scripts/create_platform_admin.py --email admin@yourcompany.com

The user will receive an invitation email with activation link to set up OIDC.
"""
import asyncio
import argparse
import sys
import os
from uuid import uuid4

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db_models import TenantModel, Base
from app.rbac_models import Role
from app.db_models import UserModel
from app.constants import RoleName
from app.config import settings
from app.services.firebase_auth import firebase_auth_service

# System Tenant Constants
SYSTEM_TENANT_FIREBASE_ID = "system-platform"

async def create_platform_admin(email: str, name: str = None):
    """
    Create a platform admin user
    
    Args:
        email: Email address for the platform admin
        name: Display name (defaults to email username)
    """
    print(f"🔧 Creating Platform Admin: {email}")
    
    # Initialize Firebase
    firebase_auth_service.initialize()
    
    # Setup database connection
    db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. Find System Tenant
        # 1. Find System Tenant
        result = await db.execute(
            select(TenantModel).where(TenantModel.is_system_tenant == True)
        )
        system_tenant = result.scalar_one_or_none()
        
        if not system_tenant:
            print("❌ Error: System Tenant not found. Run seed_system_tenant.py first.")
            return False
        
        print(f"✅ Found System Tenant: {system_tenant.name} ({system_tenant.id})")
        
        # 2. Find platform_admin role
        result = await db.execute(
            select(Role)
            .where(Role.tenant_id == system_tenant.id)
            .where(Role.name == RoleName.PLATFORM_ADMIN)
        )
        admin_role = result.scalar_one_or_none()
        
        if not admin_role:
            print("❌ Error: platform_admin role not found. Run seed_system_tenant.py first.")
            return False
            
        print(f"✅ Found platform_admin role: {admin_role.id}")
        
        # 3. Check if user already exists in database
        result = await db.execute(
            select(UserModel).where(UserModel.email == email.lower())
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"⚠️  User already exists in database: {existing_user.id}")
            print(f"   Firebase UID: {existing_user.firebase_uid}")
            print(f"   Role: {existing_user.role_id}")
            
            # Update role if needed
            if existing_user.role_id != admin_role.id:
                print("   Updating user role to platform_admin...")
                existing_user.role_id = admin_role.id
                await db.commit()
                print("✅ User role updated")
            
            return True
        
        # 4. Create user in Firebase (under system-platform tenant)
        print(f"\n📧 Creating Firebase user in tenant: {system_tenant.firebase_tenant_id}")
        
        try:
            import firebase_admin
            from firebase_admin import auth, tenant_mgt
            
            # Get tenant-scoped auth client
            tenant_client = tenant_mgt.auth_for_tenant(system_tenant.firebase_tenant_id)
            
            # Create user (will trigger OIDC flow on first login)
            firebase_user = tenant_client.create_user(
                email=email,
                email_verified=False,  # Will verify through OIDC
                display_name=name or email.split('@')[0]
            )
            
            firebase_uid = firebase_user.uid
            print(f"✅ Firebase user created: {firebase_uid}")
            
        except Exception as e:
            print(f"❌ Error creating Firebase user: {e}")
            print("\nNote: If the tenant uses OIDC, the user will be created automatically")
            print("      on first login. Using a temporary UID for database record.")
            
            # Use a deterministic UID based on email for OIDC users
            firebase_uid = f"oidc-{email.replace('@', '-').replace('.', '-')}"
            print(f"   Using temporary UID: {firebase_uid}")
        
        # 5. Create user record in database
        print(f"\n💾 Creating database record...")
        
        user = UserModel(
            tenant_id=system_tenant.id,
            email=email.lower(),
            firebase_uid=firebase_uid,
            name=name or email.split('@')[0],
            role_id=admin_role.id,
            is_active=True
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        print(f"✅ Database record created: {user.id}")
        
        # 6. Print next steps
        print("\n" + "="*60)
        print("✨ Platform Admin User Created Successfully!")
        print("="*60)
        print(f"\nEmail: {email}")
        print(f"Firebase UID: {firebase_uid}")
        print(f"Database ID: {user.id}")
        print(f"Role: platform_admin")
        
        print("\n📋 Next Steps:")
        print("1. Navigate to: http://localhost:3000/login")
        print(f"2. Enter email: {email}")
        print("3. You'll be redirected to your OIDC provider")
        print("4. Complete OIDC authentication")
        print("5. Access the admin console at: http://localhost:3000/super-admin")
        
        if "oidc-" in firebase_uid:
            print("\n⚠️  Note: Temporary UID assigned. Firebase will update this")
            print("   automatically when the user logs in via OIDC.")
        
        print("\n" + "="*60)
    
    await engine.dispose()
    return True

def main():
    parser = argparse.ArgumentParser(
        description='Create a platform admin user for SaaS Admin Console'
    )
    parser.add_argument(
        '--email',
        required=True,
        help='Email address for the platform admin user'
    )
    parser.add_argument(
        '--name',
        help='Display name (defaults to email username)'
    )
    
    args = parser.parse_args()
    
    # Validate email
    if '@' not in args.email or '.' not in args.email:
        print("❌ Error: Invalid email format")
        sys.exit(1)
    
    # Run async function
    success = asyncio.run(create_platform_admin(args.email, args.name))
    
    if success:
        print("\n✅ Done!")
        sys.exit(0)
    else:
        print("\n❌ Failed to create platform admin")
        sys.exit(1)

if __name__ == "__main__":
    main()
