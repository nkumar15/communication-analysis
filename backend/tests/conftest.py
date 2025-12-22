"""
Pytest configuration and shared fixtures for E2E testing - SIMPLIFIED VERSION
"""
import os

# Set TESTING flag BEFORE importing app (enables Celery eager mode for sync task execution)
os.environ['TESTING'] = 'true'

import asyncio
import pytest
import pytest_asyncio
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import secrets

# Import app components
from tests.test_app import app  # Unified test app with all routers
from core.db.session import get_db
from core.db.base import Base
from core.config import settings
from core.utils import get_utc_now


# Test database URL (shared connection)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")  



# Create a single test engine and session factory
test_engine = None
test_session_factory = None


# ============================================================================
# Tenant-Aware Session Wrapper
# ============================================================================

class TenantAwareSession:
    """
    Wrapper around AsyncSession that automatically manages tenant context.
    
    This ensures ALL database operations respect RLS tenant isolation.
    Tenant context is set automatically before any database operation.
    """
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self._session = session
        self._tenant_id = tenant_id
        self._context_set = False
    
    async def _ensure_context(self):
        """
        Automatically set tenant context before any operation.
        
        Note: SET LOCAL is transaction-scoped, so we re-set it for each execute()
        to handle cases where transactions have been committed/rolled back.
        """
        from core.db.rls import rls_service
        await rls_service.set_tenant_context(self._session, self._tenant_id)
    
    async def execute(self, *args, **kwargs):
        """Execute with automatic tenant context"""
        await self._ensure_context()
        return await self._session.execute(*args, **kwargs)
    
    async def commit(self):
        await self._session.commit()
        self._context_set = False  # Reset for next transaction
    
    async def rollback(self):
        await self._session.rollback()
        self._context_set = False
    
    async def flush(self):
        await self._ensure_context()
        await self._session.flush()
    
    async def refresh(self, instance):
        await self._ensure_context()
        await self._session.refresh(instance)
    
    def add(self, instance):
        self._session.add(instance)
    
    async def delete(self, instance):
        await self._ensure_context()
        await self._session.delete(instance)
    
    async def begin(self):
        return await self._session.begin()
    
    async def begin_nested(self):
        return await self._session.begin_nested()
    
    async def close(self):
        await self._session.close()
    
    # Delegate all other methods to underlying session
    def __getattr__(self, name):
        return getattr(self._session, name)


# ============================================================================
# Test Database Fixtures
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """Create test database engine for session"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_db_engine) -> AsyncSession:
    """Create a fresh database session for each test"""
    async_session_factory = async_sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_factory() as session:
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()




@pytest_asyncio.fixture
async def api_client(db_session):
    """Create API client with dependency overrides"""
    
    # Override database dependency to use test session
    async def override_get_db():
        # CRITICAL FIX for Test Gaps:
        # For B2B: We MUST reset the RLS context before giving the session to the API endpoint.
        # Otherwise, the API inherits the context set during test setup (seed data),
        # masking bugs where the API forgets to set its own context.
        #
        # For B2C: The auth middleware SETS the context, and we need to PRESERVE it.
        # Check if context is already set (B2C case) and don't clear it.
        from core.db.rls import rls_service
        from sqlalchemy import text
        
        # Check if RLS context is already set (B2C auth middleware sets it)
        try:
            result = await db_session.execute(
                text("SELECT current_setting('app.current_user_id', true)")
            )
            current_context = result.scalar()
            context_was_set = bool(current_context and current_context != '')
        except:
            context_was_set = False
        
        # Only clear if context was NOT already set (B2B case)
        if not context_was_set:
            await rls_service.clear_context(db_session)
        
        yield db_session
        await db_session.flush()
    
    # Override auth dependency to verify mock tokens
    from core.middleware.auth import get_current_user, bearer_scheme
    from modules.b2b.middleware.b2b_auth import get_current_active_user
    from fastapi import Depends, HTTPException, status
    from fastapi.security import HTTPAuthorizationCredentials
    from modules.b2b.models.user import UserModel
    from modules.b2b.models.rbac import Role
    from sqlalchemy import select
    import json 
    import base64
    
    async def override_get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
    ):
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        token = credentials.credentials
        try:
            # Simple decode of our mock token format: header.payload.signature
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid token format")
                
            payload_str = parts[1]
            # Add padding if needed
            payload_str += "=" * ((4 - len(payload_str) % 4) % 4)
            payload_json = base64.urlsafe_b64decode(payload_str).decode()
            return json.loads(payload_json)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    # Override B2C auth dependency for B2C endpoints
    from modules.b2c.middleware.b2c_auth import get_current_b2c_user
    
    async def override_get_current_b2c_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
        # NOTE: We use db_session directly here, NOT override_get_db
        # because override_get_db clears RLS context for B2B testing,
        # but B2C needs to SET context in the auth middleware
    ):
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        token = credentials.credentials
        try:
            # Decode mock JWT token
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid token format")
            
            payload_str = parts[1]
            payload_str += "=" * ((4 - len(payload_str) % 4) % 4)
            payload_json = base64.urlsafe_b64decode(payload_str).decode()
            payload = json.loads(payload_json)
            
            firebase_uid = payload.get("uid")
            
            # Look up actual B2C user by firebase_uid to get UUID and set RLS
            from modules.b2c.models.user import B2CUser
            from sqlalchemy import text
            
            # Use SECURITY DEFINER function to lookup user (bypasses RLS)
            result = await db_session.execute(
                text("SELECT b2c.lookup_user_by_firebase_uid(:uid)"),
                {"uid": firebase_uid}
            )
            user_id = result.scalar_one_or_none()
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Set RLS context - this is critical for B2C queries
            await db_session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
            
            # Fetch full user
            result = await db_session.execute(
                select(B2CUser).where(B2CUser.id == user_id)
            )
            user = result.scalar_one()
            
            # Fix: Check for deleted user (matches real middleware behavior)
            if user.deleted_at:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User account not found"
                )
            
            # Return user data matching what the real middleware returns
            return {
                "id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "email_verified": payload.get("email_verified", True)
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    app.dependency_overrides[get_current_b2c_user] = override_get_current_b2c_user
    # Removed override_get_current_active_user to verify real middleware logic
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def platform_admin_setup(db_session: AsyncSession):
    """Setup System Tenant, Platform Admin Role, and User"""
    from sqlalchemy import select
    from modules.platform.models import PlatformTenant, PlatformRole, PlatformUser
    from core.constants import PlatformRoleName
    
    # Generate unique identifiers for this test run
    unique_suffix = uuid4().hex[:8]
    
    # 1. Check/Create System Tenant (PlatformTenant)
    # Platform tenant is a SINGLETON - check for ANY existing one
    result = await db_session.execute(select(PlatformTenant))
    system_tenant = result.scalar_one_or_none()
    
    if not system_tenant:
        system_tenant = PlatformTenant(
            name="System Tenant",
            firebase_tenant_id="system-platform",
            is_active=True
        )
        db_session.add(system_tenant)
        await db_session.flush()
    
    # 2. Check/Create Platform Admin Role
    result = await db_session.execute(
        select(PlatformRole)
        .where(PlatformRole.name == PlatformRoleName.PLATFORM_ADMIN)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        role = PlatformRole(
            name=PlatformRoleName.PLATFORM_ADMIN,
            display_name="Platform Admin",
            is_system_role=True
        )
        db_session.add(role)
        await db_session.flush()
    
    # 3. Create Platform Admin User with UNIQUE email per test
    # This avoids IntegrityError when tests run in parallel or sequentially
    unique_email = f"admin-{unique_suffix}@system.local"
    admin_user = PlatformUser(
        platform_tenant_id=system_tenant.id,
        platform_role_id=role.id,
        email=unique_email,
        firebase_uid=f"firebase-admin-{unique_suffix}",
        display_name="Platform Admin",
        is_active=True
    )
    db_session.add(admin_user)
    await db_session.flush()
    
    # Don't commit - let the test session handle rollback
    
    return {
        "tenant": system_tenant,
        "user": admin_user,
        "token": encode_mock_jwt(create_mock_firebase_token(
            uid=admin_user.firebase_uid,
            email=admin_user.email,
            firebase_tenant_id=system_tenant.firebase_tenant_id
        ))
    }


@pytest_asyncio.fixture
async def platform_admin_token(platform_admin_setup):
    """Fixture to provide platform admin token directly"""
    return platform_admin_setup["token"]


# Helper functions (not fixtures - just plain functions)

async def set_tenant_context(db_session: AsyncSession, tenant_id: UUID) -> None:
    """
    Set tenant context for RLS in test database session
    
    Call this before making verification queries in tests to ensure
    RLS policies allow the SELECT operations.
    
    Example:
        await set_tenant_context(db_session, tenant.id)
        result = await db_session.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one()
    """
    from core.db.rls import rls_service
    await rls_service.set_tenant_context(db_session, tenant_id)


@pytest_asyncio.fixture
async def b2b_test_setup(db_session: AsyncSession):
    """
    Standard B2B test setup with tenant + admin user + tenant-aware session.
    
    This fixture creates a complete test environment with automatic tenant isolation:
    - Creates a test tenant
    - Creates an admin user  
    - Generates an auth token
    - Returns a TenantAwareSession that automatically sets RLS context
    
    Usage:
        async def test_something(api_client, b2b_test_setup):
            setup = b2b_test_setup
            # API calls with token
            response = await api_client.post(..., headers={"Authorization": f"Bearer {setup['token']}"})
            # Database verification with automatic context
            result = await setup['session'].execute(select(Team).where(...))
    """
    # Step 1: Create tenant (which will set its own context for role seeding)
    tenant = await create_test_tenant(db_session)
    
    # Step 2: Create TenantAwareSession for this tenant
    tenant_session = TenantAwareSession(db_session, tenant.id)
    
    # Step 3: Create admin user using tenant-aware session
    admin = await create_test_user(
        tenant_session,  # Use tenant-aware session
        tenant_id=tenant.id,
        email=f"admin@{tenant.domain}",
        role_slug="admin"
    )
    
    # Step 4: Create token
    token = encode_mock_jwt(create_mock_firebase_token(
        uid=admin.firebase_uid,
        email=admin.email,
        firebase_tenant_id=tenant.firebase_tenant_id # FIX: Use actual tenant ID
    ))
    
    return {
        "tenant": tenant,
        "admin": admin,
        "token": token,
        "session": tenant_session,  # Use this for all DB operations
        "tenant_id": tenant.id,
    }





def create_mock_firebase_token(
    uid: str,
    email: str,
    email_verified: bool = True,
    firebase_tenant_id: str = "test-tenant",
    name: str = None
) -> Dict[str, Any]:
    """Create a mock Firebase JWT token payload"""
    return {
        "uid": uid,
        "email": email,
        "email_verified": email_verified,
        "name": name or email.split("@")[0],
        "firebase": {
            "tenant": firebase_tenant_id,
            "sign_in_provider": "oidc.auth0"
        },
        "iss": "https://securetoken.google.com/test-project",
        "aud": "test-project",
        "auth_time": int(get_utc_now().timestamp()),
        "iat": int(get_utc_now().timestamp()),
        "exp": int((get_utc_now() + timedelta(hours=1)).timestamp()),
    }


def encode_mock_jwt(payload: Dict[str, Any]) -> str:
    """Create a fake JWT string for testing"""
    import json, base64
    header = base64.b64encode(json.dumps({"alg": "mock", "typ": "JWT"}).encode()).decode()
    payload_encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    signature = "mock_signature"
    return f"{header}.{payload_encoded}.{signature}"


def create_auth_headers(user, tenant=None):
    """
    Create authentication headers for API requests.
    
    Simplifies test authentication by automatically creating proper JWT headers
    from user and tenant objects.
    
    Args:
        user: User object with firebase_uid and email attributes
        tenant: Tenant object with firebase_tenant_id attribute (optional)
                If not provided, uses "test-tenant" as default
    
    Returns:
        dict: Headers dictionary with Authorization bearer token
        
    Example:
        headers = create_auth_headers(owner, tenant)
        response = await api_client.get("/api/endpoint", headers=headers)
    """
    # Auto-detect tenant from user if not provided
    if tenant is None and hasattr(user, 'tenant'):
        tenant = user.tenant
    
    firebase_tenant_id = tenant.firebase_tenant_id if tenant else "test-tenant"
    
    token = encode_mock_jwt(create_mock_firebase_token(
        uid=user.firebase_uid,
        email=user.email,
        firebase_tenant_id=firebase_tenant_id
    ))
    
    return {"Authorization": f"Bearer {token}"}


# Direct async helper functions (not fixtures)

async def ensure_rbac_seeds(db_session: AsyncSession):
    """Ensure basic RBAC data (Resources, Actions, Templates) exists"""
    from modules.b2b.models.rbac import Resource, Action
    from modules.b2b.models.role_template import RoleTemplate
    from sqlalchemy import select
    from core.constants import B2BRoleName

    # 1. Resources
    # Must match resources.yaml
    resources = [
        ("users", True), 
        ("roles", True), 
        ("settings", True), 
        ("audit_logs", True),
        ("billing", True),
        ("invoices", True),
        ("teams", False),
        ("team_members", False),
        ("projects", False),
        ("tasks", False),
        ("comments", False)
    ]
    existing_res = await db_session.execute(select(Resource.name))
    existing_res_names = set(existing_res.scalars().all())
    
    for name, is_system in resources:
        if name not in existing_res_names:
            db_session.add(Resource(
                name=name,
                display_name=name.replace('_', ' ').title(),
                is_system_resource=is_system
            ))
    
    # 2. Actions
    actions = ["read", "write", "delete", "create", "admin", "invite", "manage", "export"]
    existing_act = await db_session.execute(select(Action.name))
    existing_act_names = set(existing_act.scalars().all())
    
    for a in actions:
        if a not in existing_act_names:
            db_session.add(Action(name=a, display_name=a.title()))
            
    # 3. Role Templates
    # We need to ensure we cover: admin, owner, member, viewer
    # Grant basic permissions to unblock tests
    all_perms = [
        {"resource": "users", "actions": ["read", "write", "create", "delete", "invite"]},
        {"resource": "roles", "actions": ["read", "write", "create", "delete"]},
        {"resource": "settings", "actions": ["read", "write"]},
        {"resource": "audit_logs", "actions": ["read"]},
        {"resource": "billing", "actions": ["read", "write", "manage"]},
        {"resource": "teams", "actions": ["read", "write", "delete"]},
        {"resource": "projects", "actions": ["read", "write", "delete"]},
        {"resource": "tasks", "actions": ["read", "write", "delete"]},
    ]
    read_only = [
        {"resource": "users", "actions": ["read"]},
        {"resource": "roles", "actions": ["read"]},
        {"resource": "settings", "actions": ["read"]},
        {"resource": "projects", "actions": ["read"]},
        {"resource": "tasks", "actions": ["read"]}
    ]
    
    templates = {
        "owner": {"is_default": True, "perms": all_perms}, 
        "admin": {"is_default": True, "perms": all_perms},
        "member": {"is_default": True, "perms": read_only},
        "viewer": {"is_default": True, "perms": read_only},
    }
    
    existing_tpl = await db_session.execute(select(RoleTemplate.name))
    existing_tpl_names = set(existing_tpl.scalars().all())
    
    for name, config in templates.items():
        if name not in existing_tpl_names:
            db_session.add(RoleTemplate(
                name=name,
                display_name=name.title(),
                is_default=config["is_default"],
                permissions=config["perms"]
            ))
            
    await db_session.flush()
async def create_test_tenant(
    db_session: AsyncSession,
    name: str = "Test Company",
    domain: str = "test.com",
    firebase_tenant_id: str = None,
    activation_status: str = "active"
):
    """Create a test tenant"""
    from modules.b2b.models import TenantModel
    from sqlalchemy import text
    
    if domain == "test.com":
        domain = f"test-{uuid4().hex[:8]}.com"
    
    tenant = TenantModel(
        name=name,
        domain=domain,
        firebase_tenant_id=firebase_tenant_id or f"tenant-{uuid4().hex[:8]}",
        activation_status=activation_status,
        is_active=True
    )
    db_session.add(tenant)
    await db_session.flush()  # Use flush instead of commit
    await db_session.refresh(tenant)
    
    # Set tenant context for RLS before inserting tenant-scoped data
    from core.db.rls import rls_service
    await rls_service.set_tenant_context(db_session, tenant.id)
    
    # Ensure RBAC seeds exist (Global Templates)
    await ensure_rbac_seeds(db_session)
    
    # Seed roles for this tenant using RoleTemplateService
    from modules.b2b.services.role_template_service import role_template_service
    await role_template_service.seed_tenant_roles(db_session, tenant.id)

    # Create default team
    from modules.b2b.services.team_service import create_team
    await create_team(
        db=db_session,
        tenant_id=tenant.id,
        name="Default Team",
        description="Default team for all users",
        is_default=True
    )
    
    return tenant


async def create_platform_tenant(
    db_session: AsyncSession,
    name: str = "SaaS Platform System",
    firebase_tenant_id: str = None
):
    """Create the platform tenant (singleton) - Idempotent"""
    from modules.platform.models import PlatformTenant, PlatformRole
    from sqlalchemy import select
    
    # Check if exists (singleton)
    # Check if exists (singleton)
    result = await db_session.execute(select(PlatformTenant))
    existing = result.scalar_one_or_none()
    
    tenant = existing
    if not existing:
        suffix = uuid4().hex[:8]
        firebase_tenant_id = firebase_tenant_id or f"platform-{suffix}"
        
        tenant = PlatformTenant(
            name=name,
            firebase_tenant_id=firebase_tenant_id,
            email_domain="platform.local",
            is_active=True
        )
        db_session.add(tenant)
        await db_session.flush()
        await db_session.refresh(tenant)
    
    # Ensure all system roles exist (idempotent check)
    roles = ["platform_admin", "support_staff", "billing_manager"]
    
    # Get existing roles
    existing_roles_result = await db_session.execute(
        select(PlatformRole.name)
    )
    existing_role_names = existing_roles_result.scalars().all()
    
    for role_name in roles:
        if role_name not in existing_role_names:
            role = PlatformRole(
                name=role_name,
                display_name=role_name.replace("_", " ").title(),
                is_system_role=True
            )
            db_session.add(role)
    
    await db_session.flush()
    
    return tenant


async def create_platform_user(
    db_session: AsyncSession,
    email: str,
    firebase_uid: str = None,
    role_name: str = "platform_admin",
    name: str = None,
    platform_tenant_id: UUID = None  # Optional for backward compatibility
):
    """Create a platform user - Idempotent"""
    from modules.platform.models import PlatformUser, PlatformRole, PlatformTenant
    from sqlalchemy import select
    
    # Get or create platform tenant if not provided
    if not platform_tenant_id:
        result = await db_session.execute(select(PlatformTenant))
        tenant = result.scalar_one_or_none()
        if not tenant:
            # Create minimal tenant for testing
            tenant = await create_platform_tenant(db_session)
        platform_tenant_id = tenant.id
    
    # Check if exists
    result = await db_session.execute(
        select(PlatformUser).where(PlatformUser.email == email)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    
    # Get role
    result = await db_session.execute(
        select(PlatformRole)
        .where(PlatformRole.name == role_name)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise ValueError(f"Platform role '{role_name}' not found")
    
    user = PlatformUser(
        platform_tenant_id=platform_tenant_id,
        platform_role_id=role.id,
        email=email,
        firebase_uid=firebase_uid or f"firebase-{uuid4().hex}",
        display_name=name or email.split("@")[0],
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


async def create_test_user(
    db_session: AsyncSession,
    tenant_id: UUID,
    email: str,
    firebase_uid: str = None,
    role_slug: str = "admin",
    name: str = None
):
    """Create a test user"""
    from modules.b2b.models import UserModel
    from modules.b2b.models.rbac import Role
    from sqlalchemy import select, text
    
    # Set RLS context for this user's tenant FIRST
    # This is CRITICAL because the role query below requires RLS context
    from core.db.rls import rls_service
    await rls_service.set_tenant_context(db_session, tenant_id)
    
    # Get role by slug (now with RLS context set)
    result = await db_session.execute(
        select(Role).where(Role.name == role_slug).where(Role.tenant_id == tenant_id)
    )
    role = result.scalar_one_or_none()
    
    user = UserModel(
        tenant_id=tenant_id,
        email=email,
        firebase_uid=firebase_uid or f"firebase-{uuid4().hex}",
        name=name or email.split("@")[0],
        role_id=role.id if role else None,
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


async def create_test_invitation(
    db_session: AsyncSession,
    tenant_id: UUID,
    email: str,
    role: str = "field_agent",
    invited_by: UUID = None,
    expires_in_days: int = 7,
    team_id: UUID = None,  # NEW: Optional team assignment
    team_role: str = None   # NEW: Optional team role
):
    """Create a test invitation"""
    from modules.b2b.models import InvitationModel
    from sqlalchemy import text
    
    # Set RLS context for invitation creation
    from core.db.rls import rls_service
    await rls_service.set_tenant_context(db_session, tenant_id)
    
    invitation = InvitationModel(
        tenant_id=tenant_id,
        email=email,
        role=role,
        invitation_token=secrets.token_urlsafe(32),
        invited_by=invited_by,
        team_id=team_id,        # NEW
        team_role=team_role,    # NEW
        expires_at=get_utc_now() + timedelta(days=expires_in_days)
    )
    db_session.add(invitation)
    await db_session.flush()
    await db_session.refresh(invitation)
    return invitation


# ============================================================================
# B2C Test Helpers
# ============================================================================

async def create_b2c_user(
    db_session: AsyncSession,
    email: str,
    firebase_uid: str = None,
    display_name: str = None
):
    """Create a B2C user for testing"""
    from modules.b2c.models.user import B2CUser
    from sqlalchemy import text
    
    if not firebase_uid:
        firebase_uid = f"b2c-{uuid4().hex[:12]}"
    
    # Create user with pre-generated ID so we can set RLS context
    user_id = uuid4()
    
    # Set user context to allow this user's data to be created
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
    
    user = B2CUser(
        id=user_id,
        firebase_uid=firebase_uid,
        email=email,
        display_name=display_name or email.split('@')[0]
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    
    return user


async def create_b2c_workspace(
    db_session: AsyncSession,
    owner_id: UUID,
    name: str,
    workspace_type: str = 'personal',
    subscription_tier: str = 'free'
):
    """Create a B2C workspace for testing"""
    from modules.b2c.models.workspace import Workspace, WorkspaceType
    from modules.b2c.models.workspace_member import WorkspaceMember
    from sqlalchemy import text
    
    # Set user context to owner to allow workspace creation
    await db_session.execute(text(f"SET LOCAL app.current_user_id = '{owner_id}'"))
    
    workspace = Workspace(
        name=name,
        type=WorkspaceType(workspace_type),
        owner_id=owner_id,
        subscription_tier=subscription_tier
    )
    db_session.add(workspace)
    await db_session.flush()
    await db_session.refresh(workspace)
    
    # Add owner as member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=owner_id,
        role='owner'
    )
    db_session.add(member)
    await db_session.flush()
    
    return workspace


def create_b2c_mock_token(firebase_uid: str, email: str, email_verified: bool = True):
    """Create mock Firebase token for B2C testing"""
    return {
        'uid': firebase_uid,
        'email': email,
        'email_verified': email_verified,
        'name': email.split('@')[0]
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


async def create_auth_provider(
    db_session: AsyncSession,
    tenant_id: UUID,
    provider_type: str = "oidc",
    provider_id: str = None,
    is_primary: bool = True,
    config_data: dict = None
):
    """Create an auth provider for testing SSO"""
    from modules.b2b.models.auth_provider import AuthProvider
    from sqlalchemy import select
    
    # Default provider_id if not provided
    if provider_id is None:
        provider_id = f"{provider_type}.test-provider"
    
    # Default config with OIDC settings
    if config_data is None:
        config_data = {
            "issuer": "https://test-issuer.example.com",
            "client_id": "test-client-id-12345",
            "client_secret": "test-client-secret",
        }
    
    # Check if provider already exists
    result = await db_session.execute(
        select(AuthProvider).where(
            AuthProvider.tenant_id == tenant_id,
            AuthProvider.provider_id == provider_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    
    provider = AuthProvider(
        tenant_id=tenant_id,
        provider_type=provider_type,
        provider_id=provider_id,
        display_name=f"Test {provider_type.upper()} Provider",
        is_primary=is_primary,
        is_active=True,
        config_data=config_data
    )
    
    db_session.add(provider)
    await db_session.flush()
    await db_session.refresh(provider)
    
    return provider
