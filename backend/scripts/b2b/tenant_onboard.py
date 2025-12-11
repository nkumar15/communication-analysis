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

from core.database import AsyncSessionLocal
from core.utils.firebase import firebase_auth_service
from services.platform.services.tenant_onboarding_service import tenant_onboarding_service


@click.group()
def cli():
    """Enterprise SSO Tenant Management CLI"""
    click.echo("🏢 Enterprise SSO - Tenant Management CLI\n")


@cli.command()
@click.option('--company', required=True, help='Company name')
@click.option('--domain', required=True, help='Email domain (e.g., acme.com)')
@click.option('--owner-email', required=True, help='Owner email address')
@click.option('--oidc-provider', required=True,
              type=click.Choice(['auth0', 'okta', 'google', 'azure']),
              help='OIDC provider type')
@click.option('--oidc-client-id', required=True, help='OIDC Client ID')
@click.option('--oidc-client-secret', required=True, help='OIDC Client Secret')
@click.option('--oidc-issuer', required=True, help='OIDC Issuer URL')
@click.option('--oidc-mobile-client-id', required=False, help='Mobile OIDC Client ID (optional)')
def create(company, domain, owner_email, oidc_provider,
           oidc_client_id, oidc_client_secret, oidc_issuer, oidc_mobile_client_id):
    """Create a new tenant with pre-configured SSO"""
    asyncio.run(create_tenant_async(
        company, domain, owner_email, oidc_provider,
        oidc_client_id, oidc_client_secret, oidc_issuer, oidc_mobile_client_id
    ))


async def create_tenant_async(
    company, domain, owner_email, oidc_provider,
    oidc_client_id, oidc_client_secret, oidc_issuer, oidc_mobile_client_id=None
):
    """Async tenant creation logic"""
    click.echo(f"🚀 Creating tenant for {company}...\n")
    
    async with AsyncSessionLocal() as db:
        try:
            # Explicitly set platform admin context to ensure RLS bypass works
            # The service needs this to query/create across tenants if needed
            from sqlalchemy import text
            await db.execute(text("SET LOCAL app.is_platform_admin = 'true'"))
            
            result = await tenant_onboarding_service.onboard_tenant(
                db=db,
                company_name=company,
                domain=domain,
                owner_email=owner_email,
                oidc_provider=oidc_provider,
                oidc_client_id=oidc_client_id,
                oidc_client_secret=oidc_client_secret,
                oidc_issuer=oidc_issuer,
                oidc_mobile_client_id=oidc_mobile_client_id
            )
            
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
@click.option('--oidc-web-provider-id', prompt='Web OIDC Provider ID (e.g., oidc.auth0)', help='Existing OIDC provider ID')
@click.option('--oidc-web-client-id', prompt='OIDC Client ID (for web)', required=False, help='OIDC Client ID')
@click.option('--oidc-mobile-client-id', prompt='OIDC Client ID (for mobile app)', required=False, help='Mobile Client ID')
@click.option('--oidc-mobile-provider-id', prompt='Mobile OIDC Provider ID (optional)', required=False, default=None, help='Existing Mobile OIDC provider ID')
@click.option('--oidc-issuer', prompt='OIDC Issuer URL (for mobile app)', required=False, help='OIDC Issuer URL')
@click.option('--owner-email', prompt='Owner Email', help='Owner email address')
def create_local(company, domain, firebase_tenant_id, oidc_web_provider_id, oidc_web_client_id, oidc_mobile_client_id, oidc_mobile_provider_id, oidc_issuer, owner_email):
    """Create tenant using existing Firebase tenant (DB only - for testing)"""
    asyncio.run(create_local_async(
        company, domain, firebase_tenant_id, oidc_web_provider_id, oidc_web_client_id, oidc_mobile_client_id, oidc_mobile_provider_id, oidc_issuer, owner_email
    ))


async def create_local_async(
    company, domain, firebase_tenant_id, oidc_web_provider_id, oidc_web_client_id, oidc_mobile_client_id, oidc_mobile_provider_id, oidc_issuer, owner_email):
    """Create tenant using API service (Local Mode)"""
    click.echo(f"🚀 Creating local tenant for {company}...\n")
    click.echo(f"📍 Using Firebase tenant: {firebase_tenant_id}")
    click.echo(f"📍 Using Web OIDC provider: {oidc_web_provider_id}\n")
    click.echo(f"🔍 DEBUG: Web Client ID: {oidc_web_client_id}\n")
    click.echo(f"🔍 DEBUG: Mobile Client ID: {oidc_mobile_client_id}\n")
    click.echo(f"🔍 DEBUG: Mobile Provider ID: {oidc_mobile_provider_id}\n")
    click.echo(f"🔍 DEBUG: Issuer: {oidc_issuer}\n")

    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import text
            await db.execute(text("SET LOCAL app.is_platform_admin = 'true'"))
            
            # Call service with optional ID params to skip external calls
            result = await tenant_onboarding_service.onboard_tenant(
                db=db,
                company_name=company,
                domain=domain,
                owner_email=owner_email,
                oidc_provider="oidc", # Default generic type for local
                oidc_client_id=oidc_web_client_id,
                oidc_client_secret=None,
                oidc_issuer=oidc_issuer,
                firebase_tenant_id=firebase_tenant_id,
                oidc_provider_id=oidc_web_provider_id,
                oidc_mobile_client_id=oidc_mobile_client_id,
                oidc_mobile_provider_id=oidc_mobile_provider_id
            )
            
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
    click.echo(f"OIDC Provider:    {result['oidc_provider_id']}")
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
            from sqlalchemy import text
            await db.execute(text("SET LOCAL app.is_platform_admin = 'true'"))
            
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
