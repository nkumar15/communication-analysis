from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db, close_db
from app.services.firebase_auth import firebase_auth_service
from app.routers import auth, activation, invitations, users, roles, farmers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting up application...")
    await init_db()
    firebase_auth_service.initialize()
    print("✓ Database connection established")
    print("✓ Firebase Admin SDK initialized")
    
    yield
    
    # Shutdown
    print("Shutting down application...")
    await close_db()
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
app.include_router(activation.router)
app.include_router(invitations.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(farmers.router)


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
