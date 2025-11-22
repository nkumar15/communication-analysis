#!/usr/bin/env python3
"""
Tenant CLI - Sales team tool for provisioning tenants
Usage: python -m cli.tenant_cli create --company "Acme Corp" --domain "acme.com" ...
"""
import sys
import os
import asyncio
import secrets
import click
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.database import AsyncSessionLocal
from app.db_models import TenantModel, UserModel
from app.services.firebase_auth import firebase_auth_service
from cli.firebase_admin_cli import create_firebase_tenant, configure_oidc_provider
from cli.email_service import email_service


@click.group()
def cli():
    """Enterprise SSO Tenant Management CLI"""
    click.echo("🏢 Enterprise SSO - Tenant Management CLI\n")


@cli.command()
@click.option('--company', required=True, help='Company name')
@click. option('--domain', required=True, help='Email domain (e.g., acme.com)')
@click.option('--admin-email', required=True, help='Admin email address')
@click.option('--oidc-provider', required=True,
              type=click.Choice(['auth0', 'okta', 'google', 'azure']),
              help='OIDC provider type')
@click.option('--oidc-client-id', required=True, help='OIDC Client ID')
@click.option('--oidc-client-secret', required=True, help='OIDC Client Secret')
@click.option('--oidc-issuer', required=True, help='OIDC Issuer URL')
def create(company, domain, admin_email, oidc_provider,
           oidc_client_id, oidc_client_secret, oidc_issuer):
    """Create a new tenant with pre-configured SSO"""
    asyncio.run(create_tenant_async(
        company, domain, admin_email, oidc_provider,
        oidc_client_id, oidc_client_secret, oidc_issuer
    ))


async def create_tenant_async(
    company, domain, admin_email, oidc_provider,
    oidc_client_id, oidc_client_secret, oidc_issuer
):
    """Async tenant creation logic"""
    
    click.echo(f"🚀 Creating tenant for {company}...\n")
    
    try:
        # Initialize Firebase
        firebase_auth_service.initialize()
        click.echo("✅ Firebase Admin SDK initialized")
        
        # 1. Create Firebase tenant
        click.echo("\n📍 Step 1: Creating Firebase tenant...")
        firebase_tenant_id = create_firebase_tenant(company)
        click.echo(f"✅ Firebase tenant created: {firebase_tenant_id}")
        
        # 2. Configure OIDC provider
        click.echo("\n📍 Step 2: Configuring OIDC provider...")
        provider_id = configure_oidc_provider(
            firebase_tenant_id,
            oidc_provider,
            oidc_client_id,
            oidc_client_secret,
            oidc_issuer
        )
        click.echo(f"✅ OIDC provider ID: {provider_id}")
        
        # 3. Generate activation token
        click.echo("\n📍 Step 3: Generating activation token...")
        activation_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=48)
        click.echo(f"✅ Activation token generated (expires in 48 hours)")
        
        # 4. Create tenant in database
        click.echo("\n📍 Step 4: Creating tenant in database...")
        async with AsyncSessionLocal() as db:
            tenant = TenantModel(
                name=company,
                domain=domain.lower(),
                firebase_tenant_id=firebase_tenant_id,
                oidc_provider_id=provider_id,
                activation_token=activation_token,
                activation_status='pending',
                activation_expires_at=expires_at,
                is_active=True
            )
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
            click.echo(f"✅ Tenant created: ID {tenant.id}")
        
            # 5. Create admin user
            click.echo("\n📍 Step 5: Creating admin user...")
            admin_user = UserModel(
                tenant_id=tenant.id,
                email=admin_email,
                firebase_uid="pending",  # Will be set on first login
                role='admin',
                is_active=True
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
            click.echo(f"✅ Admin user created: {admin_email}")
        
        # 6. Send activation email
        click.echo("\n📍 Step 6: Sending activation email...")
        frontend_url = settings.frontend_url or "http://localhost:3000"
        activation_url = f"{frontend_url}/activate/{activation_token}"
        
        email_service.send_activation_email(
            admin_email,
            company,
            activation_url,
            expires_at
        )
        click.echo(f"✅ Activation email sent to {admin_email}")
        
        # Summary
        click.echo("\n" + "=" * 70)
        click.echo("✅ TENANT PROVISIONED SUCCESSFULLY")
        click.echo("=" * 70)
        click.echo(f"Company:          {company}")
        click.echo(f"Domain:           {domain}")
        click.echo(f"Admin Email:      {admin_email}")
        click.echo(f"Firebase Tenant:  {firebase_tenant_id}")
        click.echo(f"OIDC Provider:    {provider_id}")
        click.echo(f"Activation URL:   {activation_url}")
        click.echo(f"Expires:          {expires_at.strftime('%Y-%m-%d %H:%M UTC')}")
        click.echo("=" * 70)
        click.echo("\n✅ Next: Admin will receive activation email")
        
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--domain', required=True, help='Tenant domain to list')
def list_tenants(domain):
    """List tenants by domain"""
    asyncio.run(list_tenants_async(domain))


async def list_tenants_async(domain):
    """List tenants"""
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


if __name__ == '__main__':
    cli()
