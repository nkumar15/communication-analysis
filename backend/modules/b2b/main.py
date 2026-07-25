"""
B2B Microservice - Tenant Management API

This microservice handles all B2B tenant-related functionality:
- Tenant activation and onboarding
- User authentication and management
- Invitations and user provisioning
- Role-based access control (RBAC)
- Domain-specific features (e.g., farming)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.db.session import engine
from core.lifespan import base_lifespan
from infrastructure.monitoring.config import setup_observability
from infrastructure.logging.middleware import LoggingMiddleware

# Import B2B routers
from modules.b2b.routers import (
    auth,
    activation,
    invitations,
    users,
    roles,
    teams,
    team_roles,
    account,
    audit_logs,
    dashboard,
    billing,
    sso_settings,
    regions,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with base_lifespan(app, "b2b-api"):
        yield

app = FastAPI(
    title="Enterprise SSO - B2B Service",
    description="Multi-tenant B2B Authentication & Management API",
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

# Add structured logging middleware
# Add structured logging middleware
app.add_middleware(LoggingMiddleware)

# Middleware to strip /api/b2b prefix if accessing directly via port 8000
@app.middleware("http")
async def strip_prefix_middleware(request, call_next):
    path = request.url.path
    if path.startswith("/api/b2b/"):
        request.scope["path"] = path.replace("/api/b2b", "", 1)
    return await call_next(request)

# Initialize Observability
setup_observability(app, service_name="b2b-api", sqlalchemy_engine=engine)

# Include routers
app.include_router(auth.router)
app.include_router(activation.router)
app.include_router(invitations.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(teams.router)
app.include_router(team_roles.router)
app.include_router(account.router)
app.include_router(audit_logs.router)
app.include_router(dashboard.router)
app.include_router(billing.router)
app.include_router(sso_settings.router)
app.include_router(regions.router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "B2B Tenant Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "b2b-api"
    }
