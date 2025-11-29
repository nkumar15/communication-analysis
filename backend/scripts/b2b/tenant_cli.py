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
import argparse
import string
from datetime import datetime, timedelta
from pathlib import Path

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import AsyncSessionLocal
from services.b2b.models import TenantModel, UserModel, InvitationModel
from core.firebase.auth_service import firebase_auth_service
from core.constants import RoleName
from scripts.core.firebase_admin_cli import create_firebase_tenant, configure_oidc_provider
from core.email import email_service


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
        db = AsyncSessionLocal()
        try:
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
            
            # 4b. Seed RBAC data
            click.echo("\n📍 Step 4b: Seeding RBAC data...")
            from pathlib import Path
            from sqlalchemy import text
            seed_path = Path(__file__).parent / "006_rbac_seed_data_simple.sql"
            seed_sql_template = seed_path.read_text()
            # Replace placeholder with actual tenant UUID
            seed_sql = seed_sql_template.replace("{tenant_id}", f"'{tenant.id}'")
            # Split by semicolon and execute each statement separately
            statements = [stmt.strip() for stmt in seed_sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
            for stmt in statements:
                await db.execute(text(stmt))
            await db.commit()
            click.echo("✅ RBAC data seeded")
        
            # 5. Create admin invitation (not user yet)
            click.echo("\n📍 Step 5: Creating admin invitation...")
            from app.services.invitation_service import invitation_service
            
            admin_invitation = await invitation_service.create_invitation(
                db=db,
                tenant_id=tenant.id,
                email=admin_email,
                role=RoleName.ADMIN,
                invitation_token=activation_token,  # Reuse activation token
                invited_by=None,  # CLI-created, no inviter
                expires_in_days=2  # 48 hours, same as activation
            )
            click.echo(f"✅ Admin invitation created: {admin_email}")
        finally:
            await db.close()
        
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


@cli.command('create-local')
@click.option('--firebase-tenant-id', prompt='Firebase Tenant ID', help='Existing Firebase tenant ID')
@click.option('--oidc-provider-id', prompt='OIDC Provider ID (e.g., oidc.auth0)', help='Existing OIDC provider ID')
@click.option('--company', prompt='Company Name', help='Company name')
@click.option('--domain', prompt='Domain (e.g., test.com)', help='Email domain')
@click.option('--admin-email', prompt='Admin Email', help='Admin email address')
def create_local(firebase_tenant_id, oidc_provider_id, company, domain, admin_email):
    """Create tenant using existing Firebase tenant (DB only - for testing)"""
    asyncio.run(create_local_async(
        firebase_tenant_id, oidc_provider_id, company, domain, admin_email
    ))


async def create_local_async(
    firebase_tenant_id, oidc_provider_id, company, domain, admin_email
):
    """Create tenant in local DB using existing Firebase tenant"""
    
    click.echo(f"🚀 Creating local tenant for {company}...\n")
    click.echo(f"📍 Using Firebase tenant: {firebase_tenant_id}")
    click.echo(f"📍 Using OIDC provider: {oidc_provider_id}\n")
    
    try:
        # 1. Generate activation token
        click.echo("📍 Step 1: Generating activation token...")
        activation_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=48)
        click.echo(f"✅ Activation token generated (expires in 48 hours)")
        
        # 2. Create tenant in database
        click.echo("\n📍 Step 2: Creating tenant in database...")
        db = AsyncSessionLocal()
        try:
            tenant = TenantModel(
                name=company,
                domain=domain.lower(),
                firebase_tenant_id=firebase_tenant_id,
                oidc_provider_id=oidc_provider_id,
                activation_token=activation_token,
                activation_status='pending',
                activation_expires_at=expires_at,
                is_active=True
            )
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
            click.echo(f"✅ Tenant created: ID {tenant.id}")
            
            # 2b. Seed RBAC data
            click.echo("\n📍 Step 2b: Seeding RBAC data...")
            from pathlib import Path
            from sqlalchemy import text
            seed_path = Path(__file__).parent / "006_rbac_seed_data_simple.sql"
            seed_sql_template = seed_path.read_text()
            # Replace placeholder with actual tenant UUID
            seed_sql = seed_sql_template.replace("{tenant_id}", f"'{tenant.id}'")
            
            # Remove comments and split by semicolon
            import re
            # Remove SQL comments (-- style)
            lines = seed_sql.split('\n')
            cleaned_lines = [line.split('--')[0] for line in lines]  # Remove inline comments
            cleaned_sql = '\n'.join(cleaned_lines)
            
            # Split by semicolon and execute each statement separately
            statements = [stmt.strip() for stmt in cleaned_sql.split(';') if stmt.strip()]
            
            click.echo(f"   Found {len(statements)} SQL statements to execute")
            for i, stmt in enumerate(statements, 1):
                try:
                    click.echo(f"   Executing statement {i}/{len(statements)}...")
                    await db.execute(text(stmt))
                except Exception as e:
                    click.echo(f"   ⚠️  Error in statement {i}: {str(e)}")
                    click.echo(f"   Statement preview: {stmt[:100]}...")
                    raise
            
            await db.commit()
            click.echo("✅ RBAC data seeded")
        
            # 3. Create admin invitation
            click.echo("\n📍 Step 3: Creating admin invitation...")
            from services.b2b.services.invitation_service import invitation_service
            
            admin_invitation = await invitation_service.create_invitation(
                db=db,
                tenant_id=tenant.id,
                email=admin_email,
                role=RoleName.ADMIN,
                invitation_token=activation_token,
                invited_by=None,
                expires_in_days=2
            )
            click.echo(f"✅ Admin invitation created: {admin_email}")
        finally:
            await db.close()
        
        # 4. Send activation email
        click.echo("\n📍 Step 4: Sending activation email...")
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
        click.echo("✅ LOCAL TENANT CREATED SUCCESSFULLY")
        click.echo("=" * 70)
        click.echo(f"Company:          {company}")
        click.echo(f"Domain:           {domain}")
        click.echo(f"Admin Email:      {admin_email}")
        click.echo(f"Firebase Tenant:  {firebase_tenant_id}")
        click.echo(f"OIDC Provider:    {oidc_provider_id}")
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
    from sqlalchemy import select, text
    
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
