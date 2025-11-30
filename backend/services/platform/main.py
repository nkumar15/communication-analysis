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
from core.database import init_db, close_db
from core.utils.firebase import firebase_auth_service

# Import logging
from core.logging import setup_logging, get_logger
from core.logging.middleware import LoggingMiddleware

# Get logger for this module
logger = get_logger(__name__)

# Import Platform router
from services.platform.routers import platform


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

# Include Platform router
app.include_router(platform.router)


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
