"""
Domain Microservice - Domain Logic API

This microservice handles domain-specific business logic:
- Farming operations and data management
- Future domain-specific features
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

# Import domain-specific routers
from services.domains.projects.routers import (
    projects_router,
    tasks_router,
    comments_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup - Initialize logging FIRST
    setup_logging(
        environment=settings.log_environment,
        log_level=settings.log_level
    )
    logger.info("domain_api_starting", service="domain-api", port=8003)
    
    await init_db()
    firebase_auth_service.initialize()
    logger.info("domain_api_ready",
                database="connected",
                firebase="initialized",
                service="domain-api")
    
    yield
    
    # Shutdown
    logger.info("domain_api_shutting_down", service="domain-api")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title="Domain Logic API",
    description="Domain-specific business logic API for projects, tasks, and comments",
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

# Include domain-specific routers
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(comments_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Domain Logic API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "domain-api"
    }
