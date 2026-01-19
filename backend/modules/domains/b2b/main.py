"""
B2B Domain Microservice - Domain Logic API

This microservice handles B2B-specific domain business logic:
- Bank Surveillance (Enron)
- Projects
- Tasks
- Comments
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# CRITICAL: Disable LlamaIndex's auto-patching of event loop (nest_asyncio)
# Monkeypatch nest_asyncio.apply to be a no-op because we use uvloop (incompatible)
import nest_asyncio
nest_asyncio.apply = lambda: None

from core.config import settings
from core.db.session import init_db, close_db, engine
from infrastructure.auth import get_auth_provider

# Import logging
from infrastructure.logging.config import setup_logging, get_logger
from infrastructure.monitoring.config import setup_observability
from infrastructure.logging.middleware import LoggingMiddleware

# Get logger for this module
logger = get_logger(__name__)

# Import domain-specific routers (B2B ONLY)
from modules.domains.b2b.task_management.routers import (
    projects_router,
    tasks_router,
    comments_router
)
from modules.domains.b2b.bank_surveillance.routers.communications import router as communications_router
from modules.domains.b2b.bank_surveillance.routers.investigations import router as investigations_router
from modules.domains.b2b.bank_surveillance.routers.graph import router as graph_router
from modules.domains.b2b.bank_surveillance.routers.ingestion import router as ingestion_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup - Initialize logging FIRST
    setup_logging(
        environment=settings.log_environment,
        log_level=settings.log_level
    )
    logger.info("b2b_domain_api_starting", service="b2b-domain-api", port=8003)
    
    await init_db()
    
    get_auth_provider().initialize()
    logger.info("b2b_domain_api_ready",
                database="connected",
                firebase="initialized",
                service="b2b-domain-api")
    
    yield
    
    # Shutdown
    logger.info("b2b_domain_api_shutting_down", service="b2b-domain-api")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title="B2B Domain Logic API",
    description="Domain-specific business logic API for B2B (Surveillance, Projects)",
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
setup_observability(app, service_name="b2b-domain-api", sqlalchemy_engine=engine)

# Include domain-specific routers
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(comments_router)
app.include_router(communications_router)
app.include_router(investigations_router)
app.include_router(graph_router)
app.include_router(ingestion_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "B2B Domain Logic API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "b2b-domain-api"
    }
