"""
B2C Domain Microservice - Domain Logic API

This microservice handles B2C-specific domain business logic:
- Finance Trader (RAG/NSE)
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

# Import domain-specific routers (B2C ONLY)
from modules.domains.b2c.finance_trader.routers.rag import router as rag_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup - Initialize logging FIRST
    setup_logging(
        environment=settings.log_environment,
        log_level=settings.log_level
    )
    logger.info("b2c_domain_api_starting", service="b2c-domain-api", port=8004)
    
    await init_db()
    
    get_auth_provider().initialize()
    logger.info("b2c_domain_api_ready",
                database="connected",
                firebase="initialized",
                service="b2c-domain-api")
    
    yield
    
    # Shutdown
    logger.info("b2c_domain_api_shutting_down", service="b2c-domain-api")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title="B2C Domain Logic API",
    description="Domain-specific business logic API for B2C (Finance Trader)",
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
setup_observability(app, service_name="b2c-domain-api", sqlalchemy_engine=engine)

# Include domain-specific routers
app.include_router(rag_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "B2C Domain Logic API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "b2c-domain-api"
    }
