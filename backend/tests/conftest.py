import os
from dotenv import load_dotenv

# Load .env.test if it exists (Priority 1)
if os.path.exists(".env.test"):
    print("DEBUG: Loading config from .env.test")
    load_dotenv(".env.test", override=True)
else:
    # Fallback to .env (Priority 2)
    print("DEBUG: Loading config from .env (fallback)")
    load_dotenv(".env")

import asyncio
import pytest
import pytest_asyncio
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware



# Import app components
from core.db.session import get_db, init_db, close_db
from core.db.base import Base
from core.config import settings
from core.utils import get_utc_now
from infrastructure.auth import get_auth_provider

# Mock langchain for environment where it is missing (e.g. CI/Test container subset)
import sys
from unittest.mock import MagicMock
if 'langchain' not in sys.modules:
    sys.modules['langchain'] = MagicMock()
    sys.modules['langchain.agents'] = MagicMock()
    sys.modules['langchain.tools'] = MagicMock()
    sys.modules['langchain.prompts'] = MagicMock()
    sys.modules['langchain.chat_models'] = MagicMock()
if 'langchain_openai' not in sys.modules:
    sys.modules['langchain_openai'] = MagicMock()

# Import ALL primary apps (sub-apps are internal to these)
from modules.b2b.main import app as b2b_app
from modules.domains.b2b.main import app as b2b_domain_app

# Register RBAC plugins at module load so plugin_registry._plugins is populated.
# ASGITransport (httpx) does not trigger the ASGI lifespan, so plugin init via
# lifespan won't happen. Registration here ensures:
#   - plugin_registry._plugins.keys() returns all 3 plugin names
#   - auth_service.get_or_sync_user builds a non-empty active_plugin_list
#   - b2b_auth.get_current_active_user passes correct enabled_plugin_names to enrich_user
# initialize() is intentionally skipped; each plugin handles missing config gracefully.
from core.rbac.plugin_registry import plugin_registry as _plugin_registry
from plugins.hierarchical_teams.plugin import HierarchicalTeamsPlugin as _HTP
from plugins.geographic_boundaries.plugin import GeographicBoundariesPlugin as _GBP
from plugins.data_classification.plugin import DataClassificationPlugin as _DCP

_plugin_registry.register(_HTP())
_plugin_registry.register(_GBP())
_plugin_registry.register(_DCP())


# ============================================================================
# Unified Test App (combines all microservice routers)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🧪 Starting unified test app...")
    await init_db()
    get_auth_provider().initialize()
    print("✓ Test app ready")

    yield

    # Shutdown
    await close_db()


# Create unified test app
app = FastAPI(
    title="Unified Test API",
    description="Test-only app with all microservice routers combined",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount ALL primary apps with their correct prefixes
# CRITICAL: Mount specific paths BEFORE generic paths to avoid shadowing!
app.mount("/api/b2b/domain", b2b_domain_app)
app.mount("/api/b2b", b2b_app)



@app.get("/")
async def root():
    return {"service": "unified-test-app", "note": "For testing only"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "test"}



# Test database URL (shared connection)
# Test database URL (shared connection)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL"))  



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
    """Create test database engine for FUNCTION scope (safe for asyncio loop isolation)"""
    url = TEST_DATABASE_URL
    # Fail-safe: Ensure async driver is used
    if "postgresql+asyncpg://" not in url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            
    # print(f"\nDEBUG: Connecting to DB with URL: {url}") # Reduced noise
    # pool_pre_ping=True needed to verify connection in function scope?
    # Yes, but each test gets new engine. Overhead is acceptable for stability.
    engine = create_async_engine(url, echo=False, pool_pre_ping=False) # False is faster for tests
    yield engine
    await engine.dispose()


# ... (omitted)

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
        # We MUST reset the RLS context before giving the session to the API endpoint.
        # Otherwise, the API inherits the context set during test setup (seed data),
        # masking bugs where the API forgets to set its own context.
        from core.db.rls import rls_service

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
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: AsyncSession = Depends(get_db)
    ):
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        token = credentials.credentials
        try:
            # Simple decode
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid token format")
                
            payload_str = parts[1]
            payload_str += "=" * ((4 - len(payload_str) % 4) % 4)
            payload_json = base64.urlsafe_b64decode(payload_str).decode()
            token_data = json.loads(payload_json)
            
            # Hydrate user from DB to get permissions
            from modules.b2b.services.user_service import user_service
            from modules.b2b.rbac import get_user_permissions
            
            # Token data has 'firebase_tenant_id' or 'email'. 
            # We need to find the user.
            # user_service.get_user_by_firebase_uid checks tenant_id. 
            # We need tenant_id from token?
            # The mock token: {"user_id": uid, "email": email, "firebase": {"tenant": ...}}
            
            firebase_uid = token_data.get("user_id")
            email = token_data.get("email")
            # We might not have tenant_id easily if it's cross-tenant test?
            # But the user is unique by firebase_uid globally usually?
            # Actually user_service.get_user_by_firebase_uid expects tenant_id.
            
            # Helper to find user across tenants?
            # Or assume we set tenant context?
            # The tests set tenant context for the DB session in override_get_db?
            # No, override_get_db clears context for B2B.
            
            # Let's try to find the user by email if needed, or scan tenants?
            # Better: The token has `firebase_tenant_id`.
            firebase_tenant_id = token_data.get("firebase", {}).get("tenant")
            
            if not firebase_uid: 
                 # Fallback to returning token data (legacy behavior)
                 return token_data

            # Find tenant by firebase_tenant_id
            from modules.b2b.services.tenant_service import tenant_service
            tenant = await tenant_service.get_tenant_by_firebase_id(db, firebase_tenant_id)
            
            if not tenant:
                 # Fallback
                 return token_data
            
            user = await user_service.get_user_by_firebase_uid(db, tenant.id, firebase_uid)
            if not user:
                return token_data
                
            # get_user_by_firebase_uid returns Pydantic User model
            # Use model_dump() if available (v2), else dict()
            if hasattr(user, 'model_dump'):
                user_dict = user.model_dump()
            else:
                user_dict = user.dict()
            
            # DEBUG
            # print(f"DEBUG AUTH: User ID type: {type(user_dict.get('id'))}, Val: {user_dict.get('id')}")
            
            user_dict['permissions'] = await get_user_permissions(user.id, db)
            
            # Enrich with plugins
            from core.rbac.plugin_registry import plugin_registry
            # Plugin registry expects dict
            user_dict = await plugin_registry.enrich_user(user_dict, db)
            
            return user_dict
            
        except Exception as e:
            # print(f"Auth Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Propagate overrides to all sub-apps
    # This is required because FastAPI sub-apps do not inherit dependency overrides from the parent.
    # Must include nested sub-apps too: b2b_domain_app mounts surveillance_app as a
    # separate FastAPI instance, so it needs overrides directly.
    from modules.domains.b2b.bank_surveillance.main import app as surveillance_app
    for sub_app in [b2b_app, b2b_domain_app, surveillance_app]:
        sub_app.dependency_overrides.update(app.dependency_overrides)
    
    # httpx 0.27+ requires ASGITransport instead of app parameter
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


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
    from core.db.session import current_tenant_id
    
    current_tenant_id.set(str(tenant_id))
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
    
    # Step 3: Create OWNER user
    # We use OWNER instead of ADMIN because many tests (Billing, Settings) require full permissions.
    # The 'admin' role intentionally lacks billing access (see saas_roles.yaml).
    owner = await create_test_user(
        tenant_session,  # Use tenant-aware session
        tenant_id=tenant.id,
        email=f"owner@{tenant.domain}",
        role_slug="owner"
    )

    # Step 4: Create token
    token = encode_mock_jwt(create_mock_firebase_token(
        uid=owner.firebase_uid,
        email=owner.email,
        firebase_tenant_id=tenant.firebase_tenant_id
    ))
    
    return {
        "tenant": tenant,
        "owner": owner,
        "admin": owner, # Alias for backward compatibility (tests expect 'admin' key)
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

