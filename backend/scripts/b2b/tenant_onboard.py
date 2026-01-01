#!/usr/bin/env python3
"""
Tenant CLI - Sales team tool for provisioning tenants
Usage: python -m cli.tenant_onboard create --company "Acme Corp" --domain "acme.com" ...
"""
import sys
import os
import asyncio
import click
# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.db.session import AsyncSessionLocal
from infrastructure.auth import get_auth_provider
from modules.platform.services.tenant_onboarding_service import tenant_onboarding_service


@click.group()
def cli():
    """Enterprise SSO Tenant Management CLI"""
    click.echo("🏢 Enterprise SSO - Tenant Management CLI\n")


@cli.command()
@click.option('--company', required=True, help='Company name')
@click.option('--domain', required=True, help='Email domain (e.g., acme.com)')
@click.option('--owner-email', required=True, help='Owner email address')
def create(company, domain, owner_email):
    """Create a new tenant (SSO configuration will be done by tenant admin)"""
    asyncio.run(create_tenant_async(
        company, domain, owner_email
    ))


async def create_tenant_async(
    company, domain, owner_email
):
    """Async tenant creation logic"""
    click.echo(f"🚀 Creating tenant for {company}...\n")
    
    async with AsyncSessionLocal() as db:
        try:
            # Explicitly set platform admin context to ensure RLS bypass works
            from core.db.rls import rls_service
            await rls_service.set_platform_admin_context(db)
            
            result = await tenant_onboarding_service.onboard_tenant(
                db=db,
                company_name=company,
                domain=domain,
                owner_email=owner_email
            )
            
            await db.commit()
            
            print_summary(result)
            
        except Exception as e:
            click.echo(f"\n❌ Error: {str(e)}", err=True)
            import traceback
            traceback.print_exc()
            sys.exit(1)


@cli.command('create-local')
@click.option('--company', help='Company name')
@click.option('--domain', help='Email domain (e.g., test.com)')
@click.option('--firebase-tenant-id', help='Existing Firebase tenant ID')
@click.option('--owner-email', help='Owner email address')
@click.option('--file', required=True, help='Path to JSON config file')
def create_local(company, domain, firebase_tenant_id, owner_email, file):
    """Create tenant using existing Firebase tenant (DB only - for testing)"""
    import json
    import uuid
    from uuid import UUID

    if not os.path.exists(file):
        click.echo(f"❌ Config file not found: {file}", err=True)
        sys.exit(1)

    try:
        with open(file, 'r') as f:
            existing_config = json.load(f)
            click.echo(f"📂 Loaded config from {file}")
    except Exception as e:
        click.echo(f"❌ Invalid config file: {e}", err=True)
        sys.exit(1)

    # Resolve parameters (CLI args > Config)
    company = company or existing_config.get("company")
    domain = domain or existing_config.get("domain")
    owner_email = owner_email or existing_config.get("owner_email")
    firebase_tenant_id = firebase_tenant_id or existing_config.get("firebase_tenant_id")
    
    tenant_id_str = existing_config.get("tenant_id")
    tenant_id = UUID(tenant_id_str) if tenant_id_str else None

    # Validate mandatory fields
    missing = []
    if not company: missing.append("company")
    if not domain: missing.append("domain")
    if not owner_email: missing.append("owner_email")
    
    if missing:
        click.echo(f"❌ Missing required fields in config or args: {', '.join(missing)}", err=True)
        sys.exit(1)

    # Determine Tenant ID strategy (if not already in config)
    if not tenant_id and company == "Demo Tenant":
        NAMESPACE_DNS = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        tenant_id = uuid.uuid5(NAMESPACE_DNS, company)
    
    if tenant_id:
        click.echo(f"   Using Tenant ID: {tenant_id}")

    # Run Async Logic
    try:
        result = asyncio.run(create_local_async(
            company, domain, firebase_tenant_id, owner_email, tenant_id
        ))
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)
        sys.exit(1)

    # Update Config File with result
    import time
    existing_config.update({
        "tenant_id": str(result["tenant_id"]),
        "domain": domain,
        "company": company,
        "owner_email": owner_email,
        "firebase_tenant_id": result.get("firebase_tenant_id"),
        "last_updated": str(time.time()),
    })
    
    try:
        with open(file, 'w') as f:
            json.dump(existing_config, f, indent=2)
            click.echo(f"💾 Saved tenant config to {file}")
    except Exception as e:
        click.echo(f"⚠️ Failed to save config: {e}", err=True)
        
    print_summary(result)


async def create_local_async(
    company, domain, firebase_tenant_id, owner_email, tenant_id=None):
    """Create tenant using API service (Local Mode) - Pure Logic"""
    click.echo(f"🚀 Creating local tenant for {company} ({domain})...")
    
    async with AsyncSessionLocal() as db:
        try:
            from core.db.rls import rls_service
            await rls_service.set_platform_admin_context(db)
            
            # Check if tenant exists first (idempotency)
            if tenant_id:
                from modules.b2b.models import TenantModel
                existing_tenant = await db.get(TenantModel, tenant_id)
                if existing_tenant:
                    click.echo(f"✅ Tenant {tenant_id} already exists in DB. Skipping creation.")
                    return {
                        "tenant_id": str(existing_tenant.id),
                        "tenant_name": existing_tenant.name,
                        "domain": existing_tenant.domain,
                        "owner_email": owner_email,
                        "firebase_tenant_id": existing_tenant.firebase_tenant_id,
                        "activation_url": "ALREADY_ACTIVE",
                        "expires_at": "N/A"
                    }

            result = await tenant_onboarding_service.onboard_tenant(
                db=db,
                company_name=company,
                domain=domain,
                owner_email=owner_email,
                firebase_tenant_id=firebase_tenant_id,
                tenant_id=tenant_id
            )
            
            await db.commit()
            return result
            
        except Exception:
            raise


def print_summary(result):
    click.echo("\n" + "=" * 70)
    click.echo("✅ TENANT PROVISIONED SUCCESSFULLY")
    click.echo("=" * 70)
    click.echo(f"Company:          {result['tenant_name']}")
    click.echo(f"Domain:           {result['domain']}")
    click.echo(f"Owner Email:      {result['owner_email']}")
    click.echo(f"Firebase Tenant:  {result['firebase_tenant_id']}")
    click.echo(f"Activation URL:   {result['activation_url']}")
    click.echo(f"Expires:          {result['expires_at']}")
    click.echo("=" * 70)
    click.echo("\n✅ Next: Owner will receive activation email")
    

@cli.command()
@click.option('--domain', required=True, help='Tenant domain to list')
def list_tenants(domain):
    """List tenants by domain"""
    asyncio.run(list_tenants_async(domain))


async def list_tenants_async(domain):
    """List tenants"""
    from modules.b2b.models import TenantModel
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TenantModel).where(TenantModel.domain == domain.lower())
        )
        tenants = result.scalars().all()
        
        if not tenants:
            click.echo(f"No tenants found for domain: {domain}")
            return
        
        for tenant in tenants:
            click.echo(f"\nTenant ID: {tenant.id}")
            click.echo(f"Name: {tenant.name}")
            click.echo(f"Status: {tenant.activation_status}")
            click.echo(f"Created: {tenant.created_at}")


@cli.command('setup-sso')
@click.option('--token', required=True, help='Activation Token')
@click.option('--provider-type', default='oidc', help='Auth provider type (oidc, google, microsoft)')
@click.option('--client-id', required=True, help='Client ID')
@click.option('--client-secret', required=True, help='Client Secret')
@click.option('--issuer', required=True, help='Issuer URL (for OIDC)')
def setup_sso(token, provider_type, client_id, client_secret, issuer):
    """(Dev) Setup SSO for a pending tenant using activation token"""
    asyncio.run(setup_sso_async(
        token, provider_type, client_id, client_secret, issuer
    ))


async def setup_sso_async(token, provider_type, client_id, client_secret, issuer):
    """Async SSO setup logic"""
    from modules.b2b.services.tenant_service import tenant_service
    from modules.b2b.services.auth_provider_service import auth_provider_service
    from modules.b2b.models import TenantModel
    
    click.echo(f"🔧 Configuring SSO for token: {token[:10]}...")
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. Validate Token to get Tenant ID
            # Use platform admin context just in case, though token validation usually doesn't need it
            # But configuring provider might need permissions?
            # Actually, this simulates the USER action, who is anonymous until activated.
            # But the service code runs in backend context.
           
            try:
                validation = await tenant_service.validate_activation_token(db, token)
            except Exception as e:
                click.echo(f"❌ Invalid Token: {str(e)}")
                return
                
            tenant_id = validation["tenant_id"]
            click.echo(f"   Identified Tenant: {validation['tenant_name']} ({validation['tenant_id']})")
            
            # Get full tenant for firebase ID
            tenant = await db.get(TenantModel, tenant_id)
            
            if tenant.activation_status != 'pending':
                click.echo("❌ Tenant is not pending activation.")
                return

            # 2. Setup Provider
            # Check if this simulates local or production?
            # It calls the service which calls firebase CLI.
            
            # Construct config dict
            config = {
                "client_id": client_id,
                "client_secret": client_secret,
                "issuer": issuer
            }
            
            click.echo(f"   Configuring {provider_type} in Identity Platform...")
            
            await auth_provider_service.setup_initial_provider(
                db=db,
                tenant_id=tenant_id,
                firebase_tenant_id=tenant.firebase_tenant_id,
                provider_type=provider_type,
                provider_config=config,
                oidc_client_id=client_id,
                oidc_client_secret=client_secret,
                oidc_issuer=issuer
            )
            
            await db.commit()
            
            click.echo("\n✅ SSO Configured Successfully!")
            click.echo("   You can now verify the login flow via the Frontend or API.")
            
        except Exception as e:
            click.echo(f"\n❌ Error: {str(e)}", err=True)
            import traceback
            traceback.print_exc()
            sys.exit(1)


@cli.command('resend')
@click.option('--tenant-id', required=False, help='Tenant UUID to resend activation')
@click.option('--domain', required=False, help='Tenant domain to resend activation')
def resend_activation(tenant_id, domain):
    """Resend activation email for a pending tenant"""
    if not tenant_id and not domain:
        click.echo("❌ Error: Must provide either --tenant-id or --domain", err=True)
        sys.exit(1)
    asyncio.run(resend_activation_async(tenant_id, domain))


async def resend_activation_async(tenant_id, domain):
    """Resend activation email"""
    from modules.b2b.models import TenantModel
    from sqlalchemy import select
    from uuid import UUID
    
    async with AsyncSessionLocal() as db:
        try:
            from core.db.rls import rls_service
            await rls_service.set_platform_admin_context(db)
            
            # Find tenant by ID or domain
            if tenant_id:
                result = await db.execute(
                    select(TenantModel).where(TenantModel.id == UUID(tenant_id))
                )
            else:
                result = await db.execute(
                    select(TenantModel).where(TenantModel.domain == domain.lower())
                )
            
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                click.echo(f"❌ Tenant not found", err=True)
                sys.exit(1)
            
            click.echo(f"📧 Resending activation for: {tenant.name} ({tenant.domain})")
            click.echo(f"   Current status: {tenant.activation_status}")
            
            if tenant.activation_status == 'active':
                click.echo("⚠️  Tenant is already active!")
                return
            
            # Call the resend service
            resend_result = await tenant_onboarding_service.resend_activation(
                db=db,
                tenant_id=tenant.id
            )
            
            await db.commit()
            
            click.echo("\n" + "=" * 70)
            click.echo("✅ ACTIVATION EMAIL RESENT")
            click.echo("=" * 70)
            click.echo(f"Tenant Id:           {resend_result['tenant_id']}")
            click.echo(f"Activation URL:   {resend_result['activation_url']}")
            click.echo(f"Expires:          {resend_result['expires_at']}")
            click.echo("=" * 70)
            
        except Exception as e:
            click.echo(f"\n❌ Error: {str(e)}", err=True)
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    cli()
