"""
B2C Domain Microservice - Domain Logic API

This microservice handles B2C-specific domain business logic:
- Finance Trader (RAG/NSE)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# CRITICAL: Disable LlamaIndex's auto-patching of event loop (nest_asyncio)
import nest_asyncio
nest_asyncio.apply = lambda: None

from core.config import settings
from core.db.session import engine
from core.lifespan import base_lifespan
from infrastructure.monitoring.config import setup_observability
from infrastructure.logging.middleware import LoggingMiddleware

# Import sub-apps
from modules.domains.b2c.finance_trader.main import app as finance_trader_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with base_lifespan(app, "b2c-domain-api"):
        yield

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

# Initialize Observability
setup_observability(app, service_name="b2c-domain-api", sqlalchemy_engine=engine)

# Mount sub-apps
app.mount("/finance_trader", finance_trader_app)

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
