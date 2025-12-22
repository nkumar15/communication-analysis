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
from infrastructure.auth import firebase_auth_service
from services.platform.services.tenant_onboarding_service import tenant_onboarding_service


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
@click.option('--company', prompt='Company Name', help='Company name')
@click.option('--domain', prompt='Domain (e.g., test.com)', help='Email domain')
@click.option('--firebase-tenant-id', prompt='Firebase Tenant ID', help='Existing Firebase tenant ID')
@click.option('--owner-email', prompt='Owner Email', help='Owner email address')
def create_local(company, domain, firebase_tenant_id, owner_email):
    """Create tenant using existing Firebase tenant (DB only - for testing)"""
    asyncio.run(create_local_async(
        company, domain, firebase_tenant_id, owner_email
    ))


async def create_local_async(
    company, domain, firebase_tenant_id, owner_email):
    """Create tenant using API service (Local Mode)"""
    click.echo(f"🚀 Creating local tenant for {company}...\n")
    click.echo(f"📍 Using Firebase tenant: {firebase_tenant_id}")

    async with AsyncSessionLocal() as db:
        try:
            from core.db.rls import rls_service
            await rls_service.set_platform_admin_context(db)
            
            # Call service with optional ID params to skip external calls
            result = await tenant_onboarding_service.onboard_tenant(
                db=db,
                company_name=company,
                domain=domain,
                owner_email=owner_email,
                firebase_tenant_id=firebase_tenant_id
            )
            
            await db.commit()
            
            print_summary(result)
            
        except Exception as e:
            click.echo(f"\n❌ Error: {str(e)}", err=True)
            import traceback
            traceback.print_exc()
            sys.exit(1)


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
    from services.b2b.models import TenantModel
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
    from services.b2b.services.tenant_service import tenant_service
    from services.b2b.services.auth_provider_service import auth_provider_service
    from services.b2b.models import TenantModel
    
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
    from services.b2b.models import TenantModel
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
