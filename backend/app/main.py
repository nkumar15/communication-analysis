from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import db
from app.services.firebase_auth import firebase_auth_service
from app.routers import auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting up application...")
    await db.connect()
    firebase_auth_service.initialize()
    print("✓ Database connection established")
    print("✓ Firebase Admin SDK initialized")
    
    yield
    
    # Shutdown
    print("Shutting down application...")
    await db.disconnect()
    print("✓ Connections closed")


# Create FastAPI application
app = FastAPI(
    title="Multitenant SSO API",
    description="Enterprise SSO API with OIDC and tenant management",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Multitenant SSO API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}
