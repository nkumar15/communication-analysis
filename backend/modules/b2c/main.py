"""
B2C Microservice - Workspace Management API

This microservice handles B2C workspace functionality:
- Personal and team workspaces
- User profiles and settings
- Workspace member management
- Subscription and billing (future)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.db.session import engine
from core.lifespan import base_lifespan
from infrastructure.monitoring.config import setup_observability
from infrastructure.logging.middleware import LoggingMiddleware

# Import B2C routers
from modules.b2c.routers import auth, workspaces, billing, invitations, plans
from modules.b2c.services.todos.router import router as todos_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with base_lifespan(app, "b2c-api"):
        yield

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

# Add structured logging middleware
app.add_middleware(LoggingMiddleware)

# Initialize Observability
setup_observability(app, service_name="b2c-api", sqlalchemy_engine=engine)

# Include B2C routers
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(todos_router, prefix="/api/b2c/workspaces", tags=["B2C Todos"])
app.include_router(billing.router)
app.include_router(plans.router)
app.include_router(invitations.router)

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
