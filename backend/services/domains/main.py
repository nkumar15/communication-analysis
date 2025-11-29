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

# Import domain-specific routers
from services.domains.farming.routers import farmers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Starting Domain API microservice...")
    await init_db()
    firebase_auth_service.initialize()
    print("✓ Database connection established")
    print("✓ Firebase Admin SDK initialized")
    print("✓ Domain API ready on port 8003")
    
    yield
    
    # Shutdown
    print("Shutting down Domain API...")
    await close_db()
    print("✓ Connections closed")


# Create FastAPI application
app = FastAPI(
    title="Domain Logic API",
    description="Domain-specific business logic API for farming and other specialized features",
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

# Include domain-specific routers
app.include_router(farmers.router)


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
