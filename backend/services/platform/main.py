"""
Platform Admin Microservice

This microservice handles platform administration:
- Platform admin authentication
- Tenant management (create, list, view)
- Tenant impersonation
- Platform-wide statistics
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import settings
from core.database import init_db, close_db, engine
from infrastructure.auth import firebase_auth_service

# Import logging
from infrastructure.logging.config import setup_logging, get_logger
from infrastructure.monitoring.config import setup_observability
from infrastructure.logging.middleware import LoggingMiddleware

# Get logger for this module
logger = get_logger(__name__)

# Import Platform routers
from services.platform.routers import platform, platform_b2b, platform_b2c, roles, invitations, billing


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup - Initialize logging FIRST
    setup_logging(
        environment=settings.log_environment,
        log_level=settings.log_level
    )
    logger.info("platform_api_starting", service="platform-api", port=8001)
    
    await init_db()
    
    # Startup: Initialize Observability (Tracing, Metrics)
    # Note: Platform API currently uses sync DB for some parts and 'engine' from 'core.database'
    setup_observability(app, service_name="platform-api", sqlalchemy_engine=engine)
    
    firebase_auth_service.initialize()
    logger.info("platform_api_ready",
                database="connected",
                firebase="initialized",
                service="platform-api")
    
    yield
    
    # Shutdown
    logger.info("platform_api_shutting_down", service="platform-api")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title="Platform Admin API",
    description="Platform administration API for managing tenants, users, and system-wide operations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
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

# Include Platform routers
app.include_router(platform.router)      # Core platform endpoints (/api/platform/config, /api/platform/auth/me)
app.include_router(platform_b2b.router)  # B2B endpoints (/api/platform/b2b/*)
app.include_router(platform_b2c.router)  # B2C endpoints (/api/platform/b2c/*)
app.include_router(roles.router)         # Platform roles management (/api/platform/roles)
app.include_router(invitations.router)   # Platform user invitations (/api/platform/invitations)
app.include_router(billing.router)       # Unified Billing Admin (Coupons, Subs, Invoices)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Platform Admin API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "platform-api"
    }
