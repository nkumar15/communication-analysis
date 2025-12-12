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
from core.database import init_db, close_db
from core.utils.firebase import firebase_auth_service

# Import logging
from core.logging import setup_logging, get_logger
from core.logging.middleware import LoggingMiddleware

# Get logger for this module
logger = get_logger(__name__)

# Import B2B routers
from services.b2b.routers import (
    auth,
    activation,
    invitations,
    users,
    roles,
    teams,
    team_roles,  # NEW: Team Role Definitions
    account,
    audit_logs,  # NEW
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("service_startup")
    await init_db()
    firebase_auth_service.initialize()
    logger.info("service_ready")
    
    yield
    
    # Shutdown
    logger.info("service_shutdown")
    await close_db()


app = FastAPI(
    title="B2B Tenant Management API",
    description="API for managing B2B tenants, users, and roles",
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

# Include B2B routers
app.include_router(auth.router)
app.include_router(activation.router)
app.include_router(invitations.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(teams.router)
app.include_router(team_roles.router)  # NEW: Team Role Definitions
app.include_router(account.router)
app.include_router(audit_logs.router)  # Audit Logs




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
