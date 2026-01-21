"""
Pytest configuration and shared fixtures for E2E testing - SIMPLIFIED VERSION
"""
import os

# Set TESTING flag BEFORE importing app (enables Celery eager mode for sync task execution)
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

# Import ALL routers for testing
from modules.b2b.routers import auth, activation, invitations, users, roles, teams, account, audit_logs, billing, sso_settings, team_roles, dashboard, regions
from modules.b2b.models import RolePermission, Resource, Action, Role
from sqlalchemy import select
from modules.domains.b2b.task_management.routers import projects, tasks, comments
from modules.domains.b2b.bank_surveillance.routers import communications, cases, alerts, regulatory, controls

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

from modules.domains.b2b.bank_surveillance.routers import analysis
from modules.platform.routers import platform, platform_b2b, platform_b2c
from modules.platform.routers import roles as platform_roles, invitations as platform_invitations, billing as platform_billing
from modules.b2c.routers import auth as b2c_auth, workspaces as b2c_workspaces, invitations as b2c_invitations


# B2C billing router requires stripe - import conditionally
try:
    from modules.b2c.routers import billing as b2c_billing
    HAS_B2C_BILLING = True
except ImportError:
    HAS_B2C_BILLING = False


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


@pytest.fixture(autouse=True)
def mock_stripe():
    """Mock Stripe globally for all tests"""
    import stripe
    from unittest.mock import MagicMock, patch
    
    with patch("stripe.Customer.create") as mock_cust_create, \
         patch("stripe.Customer.retrieve") as mock_cust_ret, \
         patch("stripe.checkout.Session.create") as mock_check_create, \
         patch("stripe.billing_portal.Session.create") as mock_portal_create, \
         patch("stripe.Subscription.retrieve") as mock_sub_ret:
        
        mock_cust_create.return_value = MagicMock(
            id="cus_test_123", 
            email="test@example.com", 
            created=1704067200
        )
        mock_cust_ret.return_value = MagicMock(
            id="cus_test_123",
            email="test@example.com"
        )
        mock_check_create.return_value = MagicMock(
            id="cs_test_123", 
            url="https://checkout.stripe.com/test_123", 
            expires_at=1704153600
        )
        mock_portal_create.return_value = MagicMock(
            url="https://billing.stripe.com/test_123"
        )
        mock_sub_ret.return_value = MagicMock(
            id="sub_test_123",
            status="active",
            current_period_start=1704067200,
            current_period_end=1706745600,
            items=MagicMock(data=[MagicMock(id="si_test_123")])
        )
        
        yield


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

# Include ALL routers
app.include_router(auth.router)
app.include_router(activation.router)
app.include_router(invitations.router)  # B2B invitations
app.include_router(users.router)
app.include_router(roles.router)  # B2B roles
app.include_router(teams.router)
app.include_router(team_roles.router)  # B2B team roles
app.include_router(account.router)
app.include_router(audit_logs.router)
app.include_router(billing.router)  # B2B billing
app.include_router(sso_settings.router)  # SSO settings
app.include_router(dashboard.router)   # Dashboard Stats
app.include_router(regions.router)     # Regions
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(communications.router)
app.include_router(cases.router)
app.include_router(alerts.router)
app.include_router(analysis.router)
app.include_router(regulatory.router)
app.include_router(controls.router)
app.include_router(platform.router)
app.include_router(platform_b2b.router)
app.include_router(platform_b2c.router)
app.include_router(platform_roles.router)  # Platform roles management
app.include_router(platform_invitations.router)  # Platform invitations
app.include_router(platform_billing.router)
app.include_router(b2c_auth.router)
app.include_router(b2c_workspaces.router)
app.include_router(b2c_invitations.router)

# Include NSE RAG router
from modules.domains.b2c.finance_trader.routers import rag as nse_rag
app.include_router(nse_rag.router)

# Include B2C billing router if stripe is available
if HAS_B2C_BILLING:
    app.include_router(b2c_billing.router)


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


# from tests.seed_utils import seed_test_database_from_yaml, clean_test_database # DELETED
from scripts.b2b.seed_rbac import seed_b2b_rbac_data

# ... (omitted)

@pytest_asyncio.fixture(scope="session")
async def seed_db():
    """
    Session-scoped fixture.
    
    NOTE: Global seeding is disabled per user request.
    Valid baseline data should be created by individual test fixtures (e.g. b2b_test_setup).
    """
    yield


@pytest_asyncio.fixture
async def db_session(test_db_engine, seed_db) -> AsyncSession:
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
    
    # httpx 0.27+ requires ASGITransport instead of app parameter
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
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
        
        # Add wildcard permissions to allow all platform operations in tests
        from modules.platform.models import PlatformPermission
        wildcard_perm = PlatformPermission(
            platform_role_id=role.id,
            resource="*",
            action="*"
        )
        db_session.add(wildcard_perm)
        await db_session.flush()
    else:
        # Relationship check: Ensure it has the wildcard permission even if role existed
        from modules.platform.models import PlatformPermission
        perm_result = await db_session.execute(
            select(PlatformPermission)
            .where(PlatformPermission.platform_role_id == role.id)
            .where(PlatformPermission.resource == "*")
        )
        if not perm_result.scalar_one_or_none():
            wildcard_perm = PlatformPermission(
                platform_role_id=role.id,
                resource="*",
                action="*"
            )
            db_session.add(wildcard_perm)
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
    
    
    # Ensure RBAC seeds exist (Global Templates)
    # Required now that global seed_db is disabled
    from scripts.b2b.seed_rbac import seed_b2b_rbac_data
    # We pass the session. This seeds GLOBAL permissions/roles if missing.
    # Note: seed_b2b_rbac_data is idempotent.
    await seed_b2b_rbac_data(db_session)
    
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
    
    # --- Seed Subscription Plans (Idempotent Global Templates) ---
    from modules.b2b.models.subscription_plan import B2BSubscriptionPlan
    
    plans_to_seed = [
        {
            "tier_key": "starter",
            "name": "Starter",
            "description": "Essential features for small teams",
            "base_price_monthly": 0,
            "base_price_yearly": 0,
            "per_seat_price_monthly": 100000,
            "per_seat_price_yearly": 1000000,
            "limits": {"max_users": 5, "max_teams": 2},
            "features": {"core": True, "rbac": "base"},
            "provider_config": {"stripe": {"monthly_price_id": "price_starter_monthly", "yearly_price_id": "price_starter_yearly"}}
        },
        {
            "tier_key": "professional",
            "name": "Professional",
            "description": "Advanced collaboration and security",
            "base_price_monthly": 500000,
            "base_price_yearly": 5000000,
            "per_seat_price_monthly": 200000,
            "per_seat_price_yearly": 2000000,
            "limits": {"max_users": 50, "max_teams": 10},
            "features": {"core": True, "rbac": "full", "dedicated_support": True},
            "provider_config": {"stripe": {"monthly_price_id": "price_professional_monthly", "yearly_price_id": "price_professional_yearly"}}
        },
        {
            "tier_key": "enterprise",
            "name": "Enterprise",
            "description": "Custom solutions for large organizations",
            "base_price_monthly": 0,
            "base_price_yearly": 0,
            "per_seat_price_monthly": 0,
            "per_seat_price_yearly": 0,
            "limits": {"max_users": -1, "max_teams": -1},
            "features": {"core": True, "rbac": "full", "plugins": ["all"]},
            "contact_required": True,
            "provider_config": {"stripe": {"monthly_price_id": "price_enterprise_monthly", "yearly_price_id": "price_enterprise_yearly"}}
        }
    ]
    
    for plan_data in plans_to_seed:
        result = await db_session.execute(
            select(B2BSubscriptionPlan).where(B2BSubscriptionPlan.tier_key == plan_data["tier_key"])
        )
        existing_plan = result.scalar_one_or_none()
        if not existing_plan:
            plan = B2BSubscriptionPlan(**plan_data)
            db_session.add(plan)
        else:
            existing_plan.provider_config = plan_data["provider_config"]
            db_session.add(existing_plan)
    
    await db_session.flush()

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

