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
from core.rbac.init_plugins import initialize_plugins

# Initialize plugins (load registry)
# initialize_plugins() -> REMOVED (Moved to async functions)


@click.group()
def cli():
    """Enterprise SSO Tenant Management CLI"""
# ...

async def _seed_teams_recursive(db, tenant_id, team_list, parent_id=None, level=0):
    """Recursively seed teams with parent-child relationships"""
    from modules.b2b.models.team import Team
    from sqlalchemy import select
    
    for t_config in team_list:
        name = t_config['name']
        desc = t_config.get('description')
        
        # Prepare config_data
        config_data = {}
        if t_config.get('region_code'):
             config_data['region_code'] = t_config.get('region_code')

        # Check if team exists by name within tenant
        stmt = select(Team).where(
            Team.tenant_id == tenant_id,
            Team.name == name
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        
        if not existing:
            new_team = Team(
                tenant_id=tenant_id,
                name=name,
                description=desc,
                parent_team_id=parent_id,
                hierarchy_level=level,
                team_type='hierarchical',
                config_data=config_data
            )
            db.add(new_team)
            await db.flush() # Need ID for children
            team_id = new_team.id
            click.echo(f"      + Created Team: {name} (Level {level})")
        else:
            team_id = existing.id
            # Update parent/level if needed
            if existing.parent_team_id != parent_id or existing.hierarchy_level != level:
                existing.parent_team_id = parent_id
                existing.hierarchy_level = level
                db.add(existing)
                await db.flush()
                click.echo(f"      ~ Updated Team Hierarchy: {name}")
            else:
                 click.echo(f"      . Team {name} exists")
        
        # Process Children
        if t_config.get('children'):
            await _seed_teams_recursive(db, tenant_id, t_config['children'], team_id, level + 1)


async def seed_plugin_config_from_yaml(db, tenant_id, yaml_path):
    """Seed plugin configuration (e.g. Regions) from YAML file"""
    import yaml
    import os
    if not os.path.exists(yaml_path):
        return

    click.echo(f"📄 Seeding plugin config from {yaml_path}")
    try:
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # 1. Geographic Boundaries
        if config.get("geographic_boundaries") and config["geographic_boundaries"].get("default_regions"):
            from modules.b2b.models.geographic_region import GeographicRegion
            from sqlalchemy import select
            
            regions = config["geographic_boundaries"]["default_regions"]
            click.echo(f"   -> Seeding {len(regions)} regions from config...")
            
            for r in regions:
                stmt = select(GeographicRegion).where(
                    GeographicRegion.tenant_id == tenant_id,
                    GeographicRegion.code == r['code']
                )
                existing = (await db.execute(stmt)).scalar_one_or_none()
                
                if not existing:
                    new_region = GeographicRegion(
                        tenant_id=tenant_id,
                        name=r['name'],
                        code=r['code'],
                    )
                    db.add(new_region)
                    click.echo(f"      + Created Region: {r['code']}")
                else:
                    click.echo(f"      . Region {r['code']} exists")

        # 2. Data Classification (Sensitivity Levels)
        if config.get("data_classification") and config["data_classification"].get("sensitivity_levels"):
            # Dynamic Table Model (since it was just created in migration and might not have ORM yet)
            # We can use raw SQL or quickly define a temporary model. Raw SQL is safer for migration scripts.
            from sqlalchemy import text
            
            levels = config["data_classification"]["sensitivity_levels"]
            click.echo(f"   -> Seeding {len(levels)} sensitivity levels from config...")
            
            for lvl in levels:
                # Check exist by level integer
                stmt = text("SELECT id FROM b2b.sensitivity_levels WHERE tenant_id = :tid AND level = :lvl")
                result = await db.execute(stmt, {"tid": tenant_id, "lvl": lvl['level']})
                existing = result.first()
                
                if not existing:
                    ins = text("""
                        INSERT INTO b2b.sensitivity_levels (tenant_id, name, level, description)
                        VALUES (:tid, :name, :lvl, :desc)
                    """)
                    await db.execute(ins, {
                        "tid": tenant_id,
                        "name": lvl['name'],
                        "lvl": lvl['level'],
                        "desc": lvl.get('description', '')
                    })
                    click.echo(f"      + Created Level: {lvl['name']} ({lvl['level']})")
                else:
                    click.echo(f"      . Level {lvl['name']} exists")

        # 3. Hierarchical Teams
        if config.get("hierarchical_teams") and config["hierarchical_teams"].get("seed_data"):
            teams_data = config["hierarchical_teams"]["seed_data"]
            click.echo(f"   -> Seeding Team Hierarchy from config...")
            await _seed_teams_recursive(db, tenant_id, teams_data)

    except Exception as e:
        click.echo(f"⚠️  Failed to seed plugin config: {e}", err=True)

async def create_local_async(
    company, domain, firebase_tenant_id, owner_email, tenant_id=None, plugins=None, subscription_tier=None, plugins_yaml_path=None):
    """Create tenant using API service (Local Mode) - Pure Logic"""
    click.echo(f"🚀 Creating local tenant for {company} ({domain})...")
    if plugins:
        click.echo(f"🔌 Plugins enabled: {plugins}")
    if subscription_tier:
        click.echo(f"💳 Subscription Tier: {subscription_tier}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Init Plugins Registry (Needed for hooks)
            await initialize_plugins(db)

            from core.db.rls import rls_service
            await rls_service.set_platform_admin_context(db)
            
            # Check if tenant exists first (idempotency)
            if tenant_id:
                from modules.b2b.models import TenantModel
                existing_tenant = await db.get(TenantModel, tenant_id)
                if existing_tenant:
                    click.echo(f"ℹ️  Tenant {tenant_id} exists. detailed configuration update...")
                    # Do NOT return early. Let the service handle repair/update logic (plugins, subscription).


            result = await tenant_onboarding_service.onboard_tenant(
                db=db,
                company_name=company,
                domain=domain,
                owner_email=owner_email,
                tenant_id=tenant_id,
                plugins=plugins,
                subscription_tier=subscription_tier
            )
            
            # Apply Plugin Config from YAML if provided
            if plugins_yaml_path:
                # We need the real tenant_id for the seeding
                # result['tenant_id'] is a string
                from uuid import UUID
                real_tenant_id = UUID(result['tenant_id'])
                await seed_plugin_config_from_yaml(db, real_tenant_id, plugins_yaml_path)
            
            await db.commit()
            return result
            
        except Exception:
            raise

# ...

async def manage_plugins_async(tenant_id, domain, enable, disable, list_only, file_path):
    """Async plugin management logic"""
    from modules.b2b.models import TenantModel
    from sqlalchemy import select
    from uuid import UUID
    from sqlalchemy.orm.attributes import flag_modified
    import json
    import os
    
    # Load from file if provided
    file_plugins = None
    if file_path:
        if not os.path.exists(file_path):
            click.echo(f"❌ Config file not found: {file_path}", err=True)
            sys.exit(1)
            
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
                click.echo(f"📂 Loaded config from {file_path}")
                
            # Resolve Identifiers if missing
            if not tenant_id and config.get("tenant_id"):
                tenant_id = config.get("tenant_id")
            if not domain and config.get("domain"):
                domain = config.get("domain")
                
            # Get plugins from file
            if "plugins" in config:
                file_plugins = config["plugins"]
                if isinstance(file_plugins, list):
                     pass
                elif file_plugins is None:
                     file_plugins = []
                else:
                     click.echo("⚠️  'plugins' in config is not a list, ignoring.")
                     file_plugins = None
                     
        except Exception as e:
            click.echo(f"❌ Invalid config file: {e}", err=True)
            sys.exit(1)

    async with AsyncSessionLocal() as db:
        try:
            # Init Plugins Registry (Needed for hooks)
            await initialize_plugins(db)
            
            from core.db.rls import rls_service
            await rls_service.set_platform_admin_context(db)
            
            # Find tenant
            if tenant_id:
                stmt = select(TenantModel).where(TenantModel.id == UUID(str(tenant_id)))
            else:
                stmt = select(TenantModel).where(TenantModel.domain == domain.lower())
                
            result = await db.execute(stmt)
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                click.echo(f"❌ Tenant not found")
                sys.exit(1)
                
            click.echo(f"🏢 Tenant: {tenant.name} ({tenant.domain})")
            
            # SYNC Strategy:
            # If file provided, we START with file state.
            # Then apply --enable / --disable on top (if mixed usage, though discouraged).
            # If no file, we start with DB state.
            
            if file_path and file_plugins is not None:
                click.echo(f"🔄 Syncing plugins from file: {file_plugins}")
                target_plugins = set(file_plugins)
            else:
                target_plugins = set(tenant.plugins or [])
            
            original_db_set = set(tenant.plugins or [])
            
            if list_only:
                click.echo(f"🔌 Active Plugins (DB): {sorted(list(original_db_set))}")
                if file_path:
                     click.echo(f"📄 Config Plugins (File): {sorted(list(target_plugins))}")
                return

            # Handle Enable
            if enable:
                to_add = [p.strip() for p in enable.split(",") if p.strip()]
                for p in to_add:
                    target_plugins.add(p)

            # Handle Disable
            if disable:
                to_remove = [p.strip() for p in disable.split(",") if p.strip()]
                for p in to_remove:
                    if p in target_plugins:
                        target_plugins.remove(p)
            
            # Use Service to Update (Handles Hooks & Validation)
            target_list = sorted(list(target_plugins))
            
            if target_list != sorted(list(original_db_set)):
                click.echo(f"⚡ Applying changes via TenantService...")
                result = await tenant_onboarding_service.tenant_service.update_tenant_plugins(
                    db=db,
                    tenant_id=tenant.id,
                    new_plugin_list=target_list
                )
                
                await db.commit()
                
                if result['added']:
                    click.echo(f"   🟢 Enabled: {result['added']}")
                if result['removed']:
                    click.echo(f"   🔴 Disabled: {result['removed']}")
                    
                click.echo(f"✅ State Updated: {result['active_plugins']}")
            else:
                click.echo(f"ℹ️  State matches Target. No changes. Active: {target_list}")
                
        except Exception as e:
            click.echo(f"\n❌ Error: {str(e)}", err=True)
            import traceback
            traceback.print_exc()
            sys.exit(1)


@cli.command()
@click.option('--company', required=True, help='Company name')
@click.option('--domain', required=True, help='Email domain (e.g., acme.com)')
@click.option('--owner-email', required=True, help='Owner email address')
@click.option('--plugins', help='Comma-separated list of plugins (e.g., geographic_boundaries)')
def create(company, domain, owner_email, plugins):
    """Create a new tenant (SSO configuration will be done by tenant admin)"""
    plugin_list = [p.strip() for p in plugins.split(",")] if plugins else None
    
    asyncio.run(create_tenant_async(
        company, domain, owner_email, plugin_list
    ))


async def create_tenant_async(
    company, domain, owner_email, plugins=None
):
    """Async tenant creation logic"""
    click.echo(f"🚀 Creating tenant for {company}...\n")
    if plugins:
        click.echo(f"🔌 Plugins enabled: {plugins}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Explicitly set platform admin context to ensure RLS bypass works
            from core.db.rls import rls_service
            await rls_service.set_platform_admin_context(db)
            
            result = await tenant_onboarding_service.onboard_tenant(
                db=db,
                company_name=company,
                domain=domain,
                owner_email=owner_email,
                plugins=plugins
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
@click.option('--plugins', help='Comma-separated list of plugins')
@click.option('--file', required=True, help='Path to JSON config file')
def create_local(company, domain, firebase_tenant_id, owner_email, plugins, file):
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
    
    # Plugins from CLI > Config > Environment (Fallback)
    plugin_str = plugins or existing_config.get("plugins")
    
    if plugin_str is not None:
        # Explicit (List or String)
        if isinstance(plugin_str, str):
            plugin_list = [p.strip() for p in plugin_str.split(",")] if plugin_str.strip() else []
        elif isinstance(plugin_str, list):
            plugin_list = plugin_str
        else:
            plugin_list = []
    else:
        # Implicit Fallback to Environment (Single Source of Truth)
        env_plugins = os.getenv("RBAC_PLUGINS", "")
        if env_plugins:
            click.echo(f"ℹ️  No plugins in config, inheriting RBAC_PLUGINS: {env_plugins}")
            plugin_list = [p.strip() for p in env_plugins.split(",") if p.strip()]
        else:
            plugin_list = []
    
    # Subscription Tier from Config
    subscription_tier = existing_config.get("subscription_tier")
    
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

    # Infer plugins.yaml path from config file path
    # Convention: If 'file' is '.../bank_surveillance_demo.json', look for '.../plugins.yaml'
    plugins_yaml_path = None
    config_dir = os.path.dirname(os.path.abspath(file))
    potential_yaml = os.path.join(config_dir, "plugins.yaml")
    if os.path.exists(potential_yaml):
        click.echo(f"   found companion config: {potential_yaml}")
        plugins_yaml_path = potential_yaml

    # Run Async Logic
    try:
        result = asyncio.run(create_local_async(
            company, domain, firebase_tenant_id, owner_email, tenant_id, plugin_list, subscription_tier, plugins_yaml_path
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
        "plugins": plugin_list if not subscription_tier else [], # If tier driven, plugins list in JSON is less relevant
        "subscription_tier": subscription_tier,
        "last_updated": str(time.time()),
    })
    
    try:
        with open(file, 'w') as f:
            json.dump(existing_config, f, indent=2)
            click.echo(f"💾 Saved tenant config to {file}")
    except Exception as e:
        click.echo(f"⚠️ Failed to save config: {e}", err=True)
        
    print_summary(result)





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


@cli.command('manage-plugins')
@click.option('--tenant-id', required=False, help='Tenant UUID')
@click.option('--domain', required=False, help='Tenant domain')
@click.option('--enable', help='Plugins to enable (comma-separated)')
@click.option('--disable', help='Plugins to disable (comma-separated)')
@click.option('--list', is_flag=True, help='List current plugins')
@click.option('--file', help='Sync state from config file (Overwrites DB)')
def manage_plugins(tenant_id, domain, enable, disable, list, file):
    """Manage plugins for an existing tenant (enable/disable features)"""
    # If file provided, logic might differ slightly (we load from file first)
    if not tenant_id and not domain and not file:
        click.echo("❌ Error: Must provide either --tenant-id, --domain, or --file", err=True)
        sys.exit(1)
        
    asyncio.run(manage_plugins_async(tenant_id, domain, enable, disable, list, file))


async def manage_plugins_async(tenant_id, domain, enable, disable, list_only, file_path):
    """Async plugin management logic"""
    from modules.b2b.models import TenantModel
    from sqlalchemy import select
    from uuid import UUID
    from sqlalchemy.orm.attributes import flag_modified
    import json
    import os
    
    # Load from file if provided
    file_plugins = None
    if file_path:
        if not os.path.exists(file_path):
            click.echo(f"❌ Config file not found: {file_path}", err=True)
            sys.exit(1)
            
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
                click.echo(f"📂 Loaded config from {file_path}")
                
            # Resolve Identifiers if missing
            if not tenant_id and config.get("tenant_id"):
                tenant_id = config.get("tenant_id")
            if not domain and config.get("domain"):
                domain = config.get("domain")
                
            # Get plugins from file
            if "plugins" in config:
                file_plugins = config["plugins"]
                if isinstance(file_plugins, list):
                     pass
                elif file_plugins is None:
                     file_plugins = []
                else:
                     click.echo("⚠️  'plugins' in config is not a list, ignoring.")
                     file_plugins = None
                     
        except Exception as e:
            click.echo(f"❌ Invalid config file: {e}", err=True)
            sys.exit(1)

    async with AsyncSessionLocal() as db:
        try:
            from core.db.rls import rls_service
            await rls_service.set_platform_admin_context(db)
            
            # Find tenant
            if tenant_id:
                stmt = select(TenantModel).where(TenantModel.id == UUID(str(tenant_id)))
            else:
                stmt = select(TenantModel).where(TenantModel.domain == domain.lower())
                
            result = await db.execute(stmt)
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                click.echo(f"❌ Tenant not found")
                sys.exit(1)
                
            click.echo(f"🏢 Tenant: {tenant.name} ({tenant.domain})")
            
            # SYNC Strategy:
            # If file provided, we START with file state.
            # Then apply --enable / --disable on top (if mixed usage, though discouraged).
            # If no file, we start with DB state.
            
            if file_path and file_plugins is not None:
                click.echo(f"🔄 Syncing plugins from file: {file_plugins}")
                target_plugins = set(file_plugins)
            else:
                target_plugins = set(tenant.plugins or [])
            
            original_db_set = set(tenant.plugins or [])
            
            if list_only:
                click.echo(f"🔌 Active Plugins (DB): {sorted(list(original_db_set))}")
                if file_path:
                     click.echo(f"📄 Config Plugins (File): {sorted(list(target_plugins))}")
                return

            # Handle Enable
            if enable:
                to_add = [p.strip() for p in enable.split(",") if p.strip()]
                for p in to_add:
                    target_plugins.add(p)

            # Handle Disable
            if disable:
                to_remove = [p.strip() for p in disable.split(",") if p.strip()]
                for p in to_remove:
                    if p in target_plugins:
                        target_plugins.remove(p)
            
            # Use Service to Update (Handles Hooks & Validation)
            target_list = sorted(list(target_plugins))
            
            if target_list != sorted(list(original_db_set)):
                click.echo(f"⚡ Applying changes via TenantService...")
                result = await tenant_onboarding_service.tenant_service.update_tenant_plugins(
                    db=db,
                    tenant_id=tenant.id,
                    new_plugin_list=target_list
                )
                
                await db.commit()
                
                if result['added']:
                    click.echo(f"   🟢 Enabled: {result['added']}")
                if result['removed']:
                    click.echo(f"   🔴 Disabled: {result['removed']}")
                    
                click.echo(f"✅ State Updated: {result['active_plugins']}")
            else:
                click.echo(f"ℹ️  State matches Target. No changes. Active: {target_list}")
                
        except Exception as e:
            click.echo(f"\n❌ Error: {str(e)}", err=True)
            import traceback
            traceback.print_exc()
            sys.exit(1)

@cli.command('set-subscription')
@click.option('--tenant-id', required=False, help='Tenant UUID')
@click.option('--domain', required=False, help='Tenant domain')
@click.option('--tier', required=True, type=click.Choice(['starter', 'professional', 'enterprise']), help='Target Subscription Tier')
def set_subscription(tenant_id, domain, tier):
    """Simulate a Subscription Upgrade/Downgrade (Production Flow)"""
    if not tenant_id and not domain:
        click.echo("❌ Error: Must provide either --tenant-id or --domain", err=True)
        sys.exit(1)
        
    asyncio.run(set_subscription_async(tenant_id, domain, tier))


async def set_subscription_async(tenant_id, domain, tier):
    """Async subscription change logic"""
    from modules.b2b.models import TenantModel
    from modules.b2b.models.subscription_plan import B2BSubscriptionPlan
    from modules.b2b.models.subscription import B2BSubscription
    from sqlalchemy import select
    from uuid import UUID
    from datetime import datetime
    
    async with AsyncSessionLocal() as db:
        try:
            from core.db.rls import rls_service
            await rls_service.set_platform_admin_context(db)
            
            # 1. Find Tenant
            if tenant_id:
                stmt = select(TenantModel).where(TenantModel.id == UUID(tenant_id))
            else:
                stmt = select(TenantModel).where(TenantModel.domain == domain.lower())
                
            tenant = await db.scalar(stmt)
            if not tenant:
                click.echo("❌ Tenant not found")
                sys.exit(1)

            # 2. Find Target Plan
            plan = await db.scalar(
                select(B2BSubscriptionPlan).where(B2BSubscriptionPlan.tier_key == tier)
            )
            if not plan:
                click.echo(f"❌ Plan '{tier}' not found in DB. Did you run 'python scripts/b2b/seed_subscription_plans.py'?")
                sys.exit(1)

            click.echo(f"🔄 Upgrading/Downgrading {tenant.name} to {plan.name}...")
            
            # 3. Extract Plugins from Plan (The Feature Flag Logic)
            target_plugins = plan.features.get('plugins', [])
            click.echo(f"   📋 Plan Features plugins: {target_plugins}")
            
            # 4. Call Service to Sync Plugins
            plugin_result = await tenant_onboarding_service.tenant_service.update_tenant_plugins(
                db=db,
                tenant_id=tenant.id,
                new_plugin_list=target_plugins
            )
            
            # 5. Update Subscription Record (The Billing Logic)
            # Find or Create subscription
            sub = await db.scalar(
                select(B2BSubscription).where(B2BSubscription.tenant_id == tenant.id)
            )
            
            if sub:
                sub.plan_id = plan.id
                sub.tier = plan.tier_key
                sub.updated_at = datetime.utcnow()
                click.echo("   💳 Updated existing subscription record.")
            else:
                 # Create wrapper if missing (simplified)
                 sub = B2BSubscription(
                     tenant_id=tenant.id,
                     plan_id=plan.id,
                     tier=plan.tier_key,
                     status='active',
                     seat_count=1,
                     base_price_cents=plan.base_price_monthly,
                     per_seat_price_cents=plan.per_seat_price_monthly,
                     total_amount_cents=plan.base_price_monthly,
                     billing_interval='monthly'
                 )
                 db.add(sub)
                 click.echo("   💳 Created new subscription record.")

            await db.commit()
            
            # Summary
            click.echo(f"\n✅ Subscription set to: {tier.upper()}")
            if plugin_result['added']: click.echo(f"   🟢 Plugins Enabled: {plugin_result['added']}")
            if plugin_result['removed']: click.echo(f"   🔴 Plugins Disabled: {plugin_result['removed']}")
            click.echo(f"   🔌 Final Active Plugins: {plugin_result['active_plugins']}")

        except Exception as e:
            click.echo(f"\n❌ Error: {str(e)}", err=True)
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    cli()
