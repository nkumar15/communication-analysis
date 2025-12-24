"""
Database connection and session management with SQLAlchemy
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from typing import AsyncGenerator
from contextvars import ContextVar
from core.config import settings

# Context variable to store current tenant ID for RLS
current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)

# Handle Database URLs robustly for Sync vs Async engines
database_url = settings.database_url

# 1. Prepare Async URL (Must have +asyncpg)
if "postgresql+asyncpg://" not in database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async engine
engine = create_async_engine(
    database_url,
    echo=False,  # Set to True for SQL query logging
    pool_size=40,
    max_overflow=20,
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

# Create sync engine for Celery workers
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 2. Prepare Sync URL (Must NOT have +asyncpg)
sync_database_url = settings.database_url
if "postgresql+asyncpg://" in sync_database_url:
    sync_database_url = sync_database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
elif sync_database_url.startswith("postgres://"):
    sync_database_url = sync_database_url.replace("postgres://", "postgresql://", 1)

sync_engine = create_engine(
    sync_database_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=sync_engine,
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
                from core.db.rls import rls_service
                from uuid import UUID
                await rls_service.set_tenant_context(session, UUID(tenant_id))
            
            # Record pool metrics
            from infrastructure.monitoring import record_db_pool_metrics
            # Access underlying pool stats (async engine wraps sync pool)
            pool = engine.sync_engine.pool
            record_db_pool_metrics(pool.size(), pool.checkedout())
            
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


# Metrics Instrumentation
from sqlalchemy import event
import time
from infrastructure.monitoring import record_db_query_duration

@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.time())

@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info["query_start_time"].pop(-1)
    
    # Simple heuristic to guess table name from statement (imperfect but useful)
    table_name = "unknown"
    query_type = "unknown"
    
    try:
        stmt = statement.strip().lower()
        if stmt.startswith("select"):
            query_type = "SELECT"
        elif stmt.startswith("insert"):
            query_type = "INSERT"
        elif stmt.startswith("update"):
            query_type = "UPDATE"
        elif stmt.startswith("delete"):
            query_type = "DELETE"
            
        # Very naive table extraction (e.g. FROM "table")
        if "from " in stmt:
            parts = stmt.split("from ")
            if len(parts) > 1:
                table_name = parts[1].split()[0].strip('";')
    except Exception:
        pass
        
    record_db_query_duration(total, query_type, table_name)
