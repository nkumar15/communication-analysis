"""
Pytest configuration and shared fixtures for E2E testing - SIMPLIFIED VERSION
"""
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
from core.database import get_db
from core.models.base import Base
from core.config import settings
from core.utils import get_utc_now


# Test database URL (shared connection)
TEST_DATABASE_URL = "postgresql+asyncpg://sso_app:sso_app_password@postgres:5432/sso_db"


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
        from sqlalchemy import text
        await self._session.execute(
            text(f"SET LOCAL app.current_tenant_id = '{str(self._tenant_id)}'")
        )
    
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
        yield db_session
    
    # Override auth dependency to verify mock tokens
    from core.middleware.auth import get_current_user, bearer_scheme
    from services.b2b.middleware.b2b_auth import get_current_active_user
    from fastapi import Depends, HTTPException, status
    from fastapi.security import HTTPAuthorizationCredentials
    from services.b2b.models.user import UserModel
    from services.b2b.models.rbac import Role
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
    # Removed override_get_current_active_user to verify real middleware logic
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def platform_admin_setup(db_session: AsyncSession):
    """Setup System Tenant, Platform Admin Role, and User"""
    from sqlalchemy import select
    from services.platform.models import PlatformTenant, PlatformRole, PlatformUser
    from core.constants import PlatformRoleName
    
    # 1. Check/Create System Tenant (PlatformTenant)
    # Check for ANY existing platform tenant due to singleton constraint
    result = await db_session.execute(select(PlatformTenant))
    system_tenant = result.scalars().first()
    
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
        .where(PlatformRole.platform_tenant_id == system_tenant.id)
        .where(PlatformRole.name == PlatformRoleName.PLATFORM_ADMIN)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        role = PlatformRole(
            platform_tenant_id=system_tenant.id,
            name=PlatformRoleName.PLATFORM_ADMIN,
            display_name="Platform Admin",
            is_system_role=True
        )
        db_session.add(role)
        await db_session.flush()
    
    # 3. Check/Create Platform Admin User
    result = await db_session.execute(
        select(PlatformUser).where(PlatformUser.email == "admin@system.local")
    )
    admin_user = result.scalar_one_or_none()
    
    if not admin_user:
        admin_user = PlatformUser(
            platform_tenant_id=system_tenant.id,
            platform_role_id=role.id,
            email="admin@system.local",
            firebase_uid=f"firebase-admin-{uuid4().hex}",
            display_name="Platform Admin",
            is_active=True
        )
        db_session.add(admin_user)
        await db_session.flush()
    
    return {
        "tenant": system_tenant,
        "user": admin_user,
        "token": encode_mock_jwt(create_mock_firebase_token(
            uid=admin_user.firebase_uid,
            email=admin_user.email,
            firebase_tenant_id=system_tenant.firebase_tenant_id
        ))
    }


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
    from sqlalchemy import text
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{str(tenant_id)}'"))


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
    import base64
    import json
    
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode()
    payload_str = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    return f"{header}.{payload_str}.test-signature"


# Direct async helper functions (not fixtures)
async def create_test_tenant(
    db_session: AsyncSession,
    name: str = "Test Company",
    domain: str = "test.com",
    firebase_tenant_id: str = None,
    activation_status: str = "active"
):
    """Create a test tenant"""
    from services.b2b.models import TenantModel
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
    from services.b2b.services.rls_service import rls_service
    await rls_service.set_tenant_context(db_session, tenant.id)
    
    # Seed roles for this tenant using RoleTemplateService
    from services.b2b.services.role_template_service import role_template_service
    await role_template_service.seed_tenant_roles(db_session, tenant.id)

    # Create default team
    from services.b2b.services.team_service import create_team
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
    from services.platform.models import PlatformTenant, PlatformRole
    from sqlalchemy import select
    
    # Check if exists (singleton)
    result = await db_session.execute(select(PlatformTenant))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    
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
    
    # Seed platform roles
    roles = ["platform_admin", "support_staff", "billing_manager"]
    for role_name in roles:
        role = PlatformRole(
            platform_tenant_id=tenant.id,
            name=role_name,
            display_name=role_name.replace("_", " ").title(),
            is_system_role=True
        )
        db_session.add(role)
    
    await db_session.flush()
    
    return tenant


async def create_platform_user(
    db_session: AsyncSession,
    platform_tenant_id: UUID,
    email: str,
    firebase_uid: str = None,
    role_name: str = "platform_admin",
    name: str = None
):
    """Create a platform user - Idempotent"""
    from services.platform.models import PlatformUser, PlatformRole
    from sqlalchemy import select
    
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
        .where(PlatformRole.platform_tenant_id == platform_tenant_id)
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
    from services.b2b.models import UserModel
    from services.b2b.models.rbac import Role
    from sqlalchemy import select, text
    
    # Set RLS context for this user's tenant FIRST
    # This is CRITICAL because the role query below requires RLS context
    from services.b2b.services.rls_service import rls_service
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
    from services.b2b.models import InvitationModel
    from sqlalchemy import text
    
    # Set RLS context for invitation creation
    from services.b2b.services.rls_service import rls_service
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
