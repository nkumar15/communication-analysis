
import asyncio
import sys
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.getcwd())

from core.config import settings
from services.b2b.models.auth_provider import AuthProvider
from services.b2b.models.tenant import TenantModel

async def update_mobile_client_id(domain: str, mobile_client_id: str):
    """
    Updates the mobile_client_id for the given tenant domain
    """
    print(f"🔌 Connecting to database: {settings.POSTGRES_SERVER}...")
    
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. Find Tenant
        result = await db.execute(select(TenantModel).where(TenantModel.domain == domain))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print(f"❌ Tenant not found for domain: {domain}")
            return
            
        print(f"✅ Found tenant: {tenant.name} ({tenant.id})")
        
        # 2. Find OIDC Provider
        result = await db.execute(
            select(AuthProvider)
            .where(AuthProvider.tenant_id == tenant.id)
            .where(AuthProvider.provider_type == 'oidc')
        )
        provider = result.scalar_one_or_none()
        
        if not provider:
            print(f"❌ No OIDC provider found for tenant.")
            return

        # 3. Update Config
        if not provider.config_data:
            provider.config_data = {}
            
        old_config = provider.config_data.copy()
        provider.config_data['mobile_client_id'] = mobile_client_id
        
        # Force update for SQLAlchemy to detect JSON change if it's a mutation
        # (Re-assigning the whole dict usually works best)
        updated_config = provider.config_data.copy()
        provider.config_data = updated_config
        
        db.add(provider)
        await db.commit()
        
        print(f"✅ Updated OIDC Config for {provider.provider_id}")
        print(f"   Old Config: {old_config}")
        print(f"   New Config: {provider.config_data}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/b2b/update_oidc_mobile.py <domain> <mobile_client_id>")
        sys.exit(1)
        
    domain = sys.argv[1]
    mobile_id = sys.argv[2]
    
    asyncio.run(update_mobile_client_id(domain, mobile_id))
