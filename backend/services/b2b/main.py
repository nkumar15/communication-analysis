"""
B2B Microservice - Tenant Management API

This microservice handles all B2B tenant-related functionality:
- Tenant activation and onboarding
- User authentication and management
- Invitations and user provisioning
- Role-based access control (RBAC)
- Domain-specific features (e.g., farming)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import settings
from core.database import init_db, close_db
from core.utils.firebase import firebase_auth_service

# Import B2B routers
from services.b2b.routers import auth, activation, invitations, users, roles

# Import domain-specific routers that belong to B2B
from services.domains.farming.routers import farmers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Starting B2B API microservice...")
    await init_db()
    firebase_auth_service.initialize()
    print("✓ Database connection established")
    print("✓ Firebase Admin SDK initialized")
    print("✓ B2B API ready on port 8000")
    
    yield
    
    # Shutdown
    print("Shutting down B2B API...")
    await close_db()
    print("✓ Connections closed")


# Create FastAPI application
app = FastAPI(
    title="B2B Tenant Management API",
    description="Multi-tenant B2B SaaS API for enterprise tenant management, authentication, and RBAC",
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

# Include B2B routers
app.include_router(auth.router)
app.include_router(activation.router)
app.include_router(invitations.router)
app.include_router(users.router)
app.include_router(roles.router)

# Include domain-specific routers
app.include_router(farmers.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "B2B Tenant Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "b2b-api"
    }
