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
from core.database import init_db, close_db
from core.utils.firebase import firebase_auth_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Starting B2C API microservice...")
    await init_db()
    firebase_auth_service.initialize()
    print("✓ Database connection established")
    print("✓ Firebase Admin SDK initialized")
    print("✓ B2C API ready on port 8002")
    
    yield
    
    # Shutdown
    print("Shutting down B2C API...")
    await close_db()
    print("✓ Connections closed")


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

# TODO: Include B2C routers when implemented
# from services.b2c.routers import workspaces, profiles
# app.include_router(workspaces.router)
# app.include_router(profiles.router)


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
