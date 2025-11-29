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


# Test database URL (shared connection)
TEST_DATABASE_URL = "postgresql+asyncpg://sso_user:sso_password@postgres:5432/sso_db"


# Create a single test engine and session factory



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
    from fastapi import Depends, HTTPException, status
    from fastapi.security import HTTPAuthorizationCredentials
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
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def platform_admin_setup(db_session: AsyncSession):
    """Setup System Tenant, Platform Admin Role, and User"""
    from sqlalchemy import select
    from services.platform.models import PlatformTenant, PlatformRole, PlatformUser
    from core.constants import RoleName
    
    # 1. Check/Create System Tenant (PlatformTenant)
    # Check for ANY existing platform tenant due to singleton constraint
    result = await db_session.execute(select(PlatformTenant))
    system_tenant = result.scalars().first()
    
    if not system_tenant:
        system_tenant = PlatformTenant(
            name="System Tenant",
            firebase_tenant_id="system-platform",
            oidc_provider_id="oidc.generic",
            is_active=True
        )
        db_session.add(system_tenant)
        await db_session.flush()
    
    # 2. Check/Create Platform Admin Role
    result = await db_session.execute(
        select(PlatformRole)
        .where(PlatformRole.platform_tenant_id == system_tenant.id)
        .where(PlatformRole.name == RoleName.PLATFORM_ADMIN)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        role = PlatformRole(
            platform_tenant_id=system_tenant.id,
            name=RoleName.PLATFORM_ADMIN,
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
            email=admin_user.email
        ))
    }


# Helper functions (not fixtures - just plain functions)
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
        "auth_time": int(datetime.utcnow().timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
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
    oidc_provider_id: str = "oidc.auth0",
    activation_status: str = "active"
):
    """Create a test tenant"""
    from services.b2b.models import TenantModel
    
    if domain == "test.com":
        domain = f"test-{uuid4().hex[:8]}.com"
    
    tenant = TenantModel(
        name=name,
        domain=domain,
        firebase_tenant_id=firebase_tenant_id or f"tenant-{uuid4().hex[:8]}",
        oidc_provider_id=oidc_provider_id,
        activation_status=activation_status,
        is_active=True
    )
    db_session.add(tenant)
    await db_session.flush()  # Use flush instead of commit
    await db_session.refresh(tenant)
    
    # Seed roles for this tenant (crucial for RBAC)
    from sqlalchemy import text
    await db_session.execute(
        text("SELECT seed_tenant_roles(:tenant_id)"),
        {"tenant_id": tenant.id}
    )
    
    return tenant


async def create_platform_tenant(
    db_session: AsyncSession,
    name: str = "SaaS Platform System",
    firebase_tenant_id: str = None,
    oidc_provider_id: str = None
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
    oidc_provider_id = oidc_provider_id or f"platform-oidc-{suffix}"
    
    tenant = PlatformTenant(
        name=name,
        firebase_tenant_id=firebase_tenant_id,
        oidc_provider_id=oidc_provider_id,
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
    from sqlalchemy import select
    
    # Get role by slug
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
    expires_in_days: int = 7
):
    """Create a test invitation"""
    from services.b2b.models import InvitationModel
    
    invitation = InvitationModel(
        tenant_id=tenant_id,
        email=email,
        role=role,
        invitation_token=secrets.token_urlsafe(32),
        invited_by=invited_by,
        expires_at=datetime.utcnow() + timedelta(days=expires_in_days)
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
