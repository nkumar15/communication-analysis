"""
Platform B2C API Router - Personal Workspace Management
All B2C-related endpoints under /api/platform/b2c/*
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel

from core.database import get_db
from services.platform.middleware.platform_auth import verify_platform_admin

router = APIRouter(
    prefix="/api/platform/b2c",
    tags=["platform-b2c"]
)

# --- Schemas ---

class B2CStats(BaseModel):
    total_workspaces: int
    personal_workspaces: int
    team_workspaces: int
    total_users: int


# --- Endpoints ---

@router.get("/stats", response_model=B2CStats)
async def get_b2c_stats(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """Get B2C platform statistics (personal workspaces)"""
    
    try:
        # Total B2C Workspaces
        total_workspaces_result = await db.execute(
            text("SELECT COUNT(*) FROM b2c.workspaces")
        )
        total_workspaces = total_workspaces_result.scalar() or 0
        
        # Personal workspaces
        personal_workspaces_result = await db.execute(
            text("SELECT COUNT(*) FROM b2c.workspaces WHERE type = 'personal'")
        )
        personal_workspaces = personal_workspaces_result.scalar() or 0
        
        # Team workspaces
        team_workspaces_result = await db.execute(
            text("SELECT COUNT(*) FROM b2c.workspaces WHERE type = 'team'")
        )
        team_workspaces = team_workspaces_result.scalar() or 0
        
        # Total B2C Users
        total_b2c_users_result = await db.execute(
            text("SELECT COUNT(*) FROM b2c.users")
        )
        total_users = total_b2c_users_result.scalar() or 0
        
    except Exception:
        # B2C schema doesn't exist - return zeros
        total_workspaces = 0
        personal_workspaces = 0
        team_workspaces = 0
        total_users = 0
    
    return B2CStats(
        total_workspaces=total_workspaces,
        personal_workspaces=personal_workspaces,
        team_workspaces=team_workspaces,
        total_users=total_users
    )


# TODO: Add B2C workspace management endpoints
# @router.get("/workspaces")
# @router.get("/workspaces/{workspace_id}")
# @router.get("/users")
# @router.get("/users/{user_id}")
