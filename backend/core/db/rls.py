"""
RLS (Row Level Security) Service

Centralized service for managing PostgreSQL RLS context.
Provides testable, reusable methods for setting and verifying tenant context.
"""
from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class RLSService:
    """Service for managing Row Level Security context"""
    
    @staticmethod
    async def set_tenant_context(db: AsyncSession, tenant_id: UUID) -> None:
        """
        Set RLS context for the current database session
        
        This executes: SET LOCAL app.current_tenant_id = '<tenant_id>'
        The setting is session-scoped and applies to all subsequent queries.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID to set as current context
        """
        await db.execute(text("RESET app.is_platform_admin"))
        await db.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
    
    @staticmethod
    async def set_user_context(db: AsyncSession, user_id: UUID) -> None:
        """
        Set RLS context for B2C (workspace-scoped isolation)
        
        This executes: SET LOCAL app.current_user_id = '<user_id>'
        Used for B2C workspace filtering via RLS policies.
        
        Args:
            db: Database session
            user_id: User UUID to set as current context
        """
        await db.execute(text("RESET app.is_platform_admin"))
        await db.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
    
    @staticmethod
    async def get_current_context(db: AsyncSession) -> Optional[UUID]:
        """
        Get the current RLS tenant context (for testing/debugging)
        
        Returns:
            Current tenant_id UUID if set, None otherwise
        """
        result = await db.execute(
            text("SELECT current_setting('app.current_tenant_id', true)")
        )
        value = result.scalar()
        
        # current_setting returns empty string if not set
        if not value or value == '':
            return None
        
        try:
            return UUID(value)
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    async def clear_context(db: AsyncSession) -> None:
        """
        Clear RLS context (mainly for testing)
        
        Note: In production, context is automatically cleared at transaction end.
        This is useful for testing scenarios where you need to reset context mid-transaction.
        """
        await db.execute(text("RESET app.current_tenant_id"))
        await db.execute(text("RESET app.current_user_id"))
        await db.execute(text("RESET app.is_platform_admin"))
    
    @staticmethod
    async def set_platform_admin_context(db: AsyncSession) -> None:
        """
        Set platform admin context to bypass RLS
        
        Platform admins need to query across all tenants.
        This sets a flag that certain queries can check to bypass RLS.
        """
        await db.execute(text("SET LOCAL app.is_platform_admin = 'true'"))


# Singleton instance
rls_service = RLSService()
