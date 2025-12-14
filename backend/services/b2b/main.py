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
from core.database import init_db, engine
from core.logging.config import setup_logging, get_logger
from core.observability.config import setup_observability
from core.logging.middleware import LoggingMiddleware

# Import B2B routers
from services.b2b.routers import (
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
)

# Setup logging first
setup_logging(environment=settings.log_environment, log_level=settings.log_level)
logger = get_logger(__name__)

logger.info(f"Starting B2B Service in {settings.log_environment} mode")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await init_db()
    
    # Startup: Initialize Observability (Tracing, Metrics)
    # We pass the engine for SQL instrumentation
    setup_observability(app, service_name="b2b-api", sqlalchemy_engine=engine)

    yield
    
    # Shutdown
    logger.info("Shutting down...")


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
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(auth.router)
app.include_router(activation.router)
app.include_router(invitations.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(teams.router)
app.include_router(team_roles.router)  # NEW: Team Role Definitions
app.include_router(account.router)
app.include_router(audit_logs.router)  # Audit Logs
app.include_router(dashboard.router)   # Dashboard Stats




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
