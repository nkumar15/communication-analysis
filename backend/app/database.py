"""
Database connection and session management with SQLAlchemy
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from typing import AsyncGenerator
from contextvars import ContextVar
from app.config import settings

# Context variable to store current tenant ID for RLS
current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)

# Convert postgres:// to postgresql+asyncpg://
database_url = settings.database_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async engine
engine = create_async_engine(
    database_url,
    echo=False,  # Set to True for SQL query logging
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session with RLS enforcement
    
    Automatically sets the PostgreSQL session variable for Row Level Security
    based on the current tenant context.
    
    Example usage in FastAPI:
        @app.get("/users")
        async def read_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(UserModel))
            users = result.scalars().all()
            return users
    """
    async with AsyncSessionLocal() as session:
        try:
            # Set tenant context for Row Level Security
            tenant_id = current_tenant_id.get()
            if tenant_id:
                # Set PostgreSQL session variable for RLS policies
                await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
            
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database connection"""
    # Test connection
    async with engine.begin() as conn:
        # Don't create tables - we use migrations
        pass


async def close_db():
    """Close database connection"""
    await engine.dispose()
