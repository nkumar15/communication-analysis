"""
Test-Only Unified App

This app includes ALL routers from all microservices for testing purposes.
In production, each service runs independently.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import settings
from core.database import init_db, close_db
from core.utils.firebase import firebase_auth_service

# Import ALL routers for testing
from services.b2b.routers import auth, activation, invitations, users, roles, teams, account, audit_logs, billing, sso_settings
from services.domains.projects.routers import projects, tasks, comments
from services.platform.routers import platform, platform_b2b, platform_b2c, roles, invitations
from services.b2c.routers import auth as b2c_auth, workspaces as b2c_workspaces, invitations as b2c_invitations

# B2C billing router requires stripe - import conditionally
try:
    from services.b2c.routers import billing as b2c_billing
    HAS_B2C_BILLING = True
except ImportError:
    HAS_B2C_BILLING = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🧪 Starting unified test app...")
    await init_db()
    firebase_auth_service.initialize()
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

# Include ALL routers
app.include_router(auth.router)
app.include_router(activation.router)
app.include_router(invitations.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(teams.router)
app.include_router(account.router)
app.include_router(audit_logs.router)
app.include_router(billing.router)  # B2B billing
app.include_router(sso_settings.router)  # SSO settings
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(platform.router)
app.include_router(platform_b2b.router)
app.include_router(platform_b2c.router)
app.include_router(roles.router)  # Platform roles management  
app.include_router(invitations.router)  # Platform invitations
app.include_router(b2c_auth.router)
app.include_router(b2c_workspaces.router)
app.include_router(b2c_invitations.router)

# Include B2C billing router if stripe is available
if HAS_B2C_BILLING:
    app.include_router(b2c_billing.router)


@app.get("/")
async def root():
    return {"service": "unified-test-app", "note": "For testing only"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "test"}
