"""
B2C Microservice - Workspace Management API

This microservice handles B2C workspace functionality:
- Personal and team workspaces
- User profiles and settings
- Workspace member management
- Subscription and billing (future)

Note: This is currently a skeleton implementation.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import settings
from core.db.session import init_db, close_db, engine
from infrastructure.auth import get_auth_provider

# Import logging
from infrastructure.logging.config import setup_logging, get_logger
from infrastructure.monitoring.config import setup_observability
from infrastructure.logging.middleware import LoggingMiddleware

# Get logger for this module
logger = get_logger(__name__)

# Import B2C routers (placeholder for future workspace management)
from modules.b2c.routers import workspaces
from modules.b2c.services.todos import router as todos_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup - Initialize logging FIRST
    setup_logging(
        environment=settings.log_environment,
        log_level=settings.log_level
    )
    logger.info("b2c_api_starting", service="b2c-api", port=8002)
    
    await init_db()
    
    # Startup: Initialize Observability (Tracing, Metrics)
    # setup_observability(app, service_name="b2c-api", sqlalchemy_engine=engine) - MOVED
    
    get_auth_provider().initialize()
    logger.info("b2c_api_ready",
                database="connected",
                firebase="initialized",
                service="b2c-api")
    
    yield
    
    # Shutdown
    logger.info("b2c_api_shutting_down", service="b2c-api")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title="B2C Workspace API",
    description="B2C workspace management API for personal and team workspaces",
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

# Initialize Observability (Tracing, Metrics)
# Must be done after app creation but before requests
setup_observability(app, service_name="b2c-api", sqlalchemy_engine=engine)

# Include B2C routers
from modules.b2c.routers import auth, workspaces, billing, invitations
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(todos_router.router, prefix="/api/b2c/workspaces", tags=["B2C Todos"])
app.include_router(billing.router)
from modules.b2c.routers import plans
app.include_router(plans.router)
app.include_router(invitations.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "B2C Workspace API",
        "version": "1.0.0",
        "status": "skeleton",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "b2c-api",
        "note": "Skeleton implementation"
    }
