from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.config import settings
from core.db.session import init_db, close_db, engine
from infrastructure.logging.config import setup_logging, get_logger
from infrastructure.auth import get_auth_provider
from infrastructure.monitoring.config import setup_observability

# Initialize logger
logger = get_logger(__name__)

def setup_app_logging():
    """Centrally configure logging based on settings."""
    setup_logging(
        environment=settings.log_environment,
        log_level=settings.log_level
    )

@asynccontextmanager
async def base_lifespan(app: FastAPI, service_name: str):
    """
    Standard base lifespan for all microservices.
    
    Handles:
    - Centralized logging setup
    - Database initialization
    - Auth provider initialization
    - Plugin registration (for B2B)
    - Observability setup
    """
    # 1. Setup Logging
    setup_app_logging()
    logger.info(f"Starting {service_name} in {settings.log_environment} mode")

    # 2. Initialize Database
    logger.info(f"[{service_name}] Initializing database...")
    await init_db()

    # 3. Initialize Auth Provider
    logger.info(f"[{service_name}] Initializing Auth Provider...")
    get_auth_provider().initialize()

    # 4. Initialize RBAC Plugins (Module specific)
    if "b2b" in service_name.lower():
        logger.info(f"[{service_name}] Initializing RBAC Plugins...")
        from core.db.session import AsyncSessionLocal
        from core.rbac.init_plugins import initialize_plugins
        async with AsyncSessionLocal() as db:
            await initialize_plugins(db)

    # 5. Initialize Observability
    # setup_observability(app, service_name=service_name, sqlalchemy_engine=engine)
    
    yield

    # Shutdown
    logger.info(f"[{service_name}] Shutting down...")
    await close_db()
