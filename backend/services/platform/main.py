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

# Import Platform router
from services.platform.routers import platform


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Starting Platform Admin API microservice...")
    await init_db()
    firebase_auth_service.initialize()
    print("✓ Database connection established")
    print("✓ Firebase Admin SDK initialized")
    print("✓ Platform Admin API ready on port 8001")
    
    yield
    
    # Shutdown
    print("Shutting down Platform Admin API...")
    await close_db()
    print("✓ Connections closed")


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
