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
from core.db.session import engine
from core.lifespan import base_lifespan
from infrastructure.monitoring.config import setup_observability
from infrastructure.logging.middleware import LoggingMiddleware

# Import Platform routers
from modules.platform.routers import platform, platform_b2b, platform_b2c, roles, invitations, billing

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with base_lifespan(app, "platform-api"):
        yield

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

# Initialize Observability
setup_observability(app, service_name="platform-api", sqlalchemy_engine=engine)

# Include Platform routers
app.include_router(platform.router)
app.include_router(platform_b2b.router)
app.include_router(platform_b2c.router)
app.include_router(roles.router)
app.include_router(invitations.router)
app.include_router(billing.router)

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
