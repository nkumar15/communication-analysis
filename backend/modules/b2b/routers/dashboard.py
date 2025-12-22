"""
Dashboard Router - Role-aware dashboard statistics
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.session import get_db
from modules.b2b.middleware import get_current_active_user
from modules.b2b.schemas.dashboard import DashboardStats
from modules.b2b.services.dashboard_service import dashboard_service


router = APIRouter(prefix="/api/b2b/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get role-aware dashboard statistics.
    
    - owner/admin: Full org visibility
    - member/viewer: Team-scoped data
    """
    user_id = current_user['id']
    tenant_id = current_user['tenant_id']
    role = current_user.get('role', 'viewer')
    
    result = await dashboard_service.get_dashboard_stats(
        db=db,
        user_id=user_id,
        tenant_id=tenant_id,
        role=role
    )
    
    return DashboardStats(**result)
