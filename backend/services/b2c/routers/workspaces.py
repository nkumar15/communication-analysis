"""
B2C Workspace Router

Endpoints for team workspace management and member administration.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from core.database import get_db
from services.b2c.middleware.b2c_auth import get_current_b2c_user
from services.b2c.services.workspace_service import workspace_service
from services.b2c.services.auth_service import auth_service
from services.b2c.models.user import B2CUser
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/b2c/workspaces", tags=["B2C Workspaces"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class CreateWorkspaceRequest(BaseModel):
    name: str
    subscription_tier: str = 'free'  # Will be validated based on actual subscription


class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = None
    settings: Optional[dict] = None


class UpdateMemberRoleRequest(BaseModel):
    role: str  # admin, member, viewer


class UpdateMemberStatusRequest(BaseModel):
    status: str  # active, suspended


# ============================================================================
# Workspace Endpoints
# ============================================================================

@router.get("/")
async def list_workspaces(
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user's workspaces (personal + team workspaces)
    
    Returns all workspaces the user is a member of
    """
    try:
        workspaces = await auth_service.get_user_workspaces(db, str(current_user['id']))
        return {"workspaces": workspaces}
        
    except Exception as e:
        logger.error(f"Error listing workspaces: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list workspaces"
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: CreateWorkspaceRequest,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create new team workspace
    
    Requires:
    - Premium or Ultimate subscription
    - Workspace quota not exceeded
    
    Auto-adds creator as owner
    """
    try:
        # Get user to determine subscription tier
        from sqlalchemy import select
        from services.b2c.models.user import B2CUser
        from services.b2c.models.workspace import Workspace
        from core.rls import rls_service
        
        # Set RLS context
        await rls_service.set_user_context(db, str(current_user['id']))
        
        # Get user's personal workspace to check subscription
        # Get user's personal workspace with subscription info
        from sqlalchemy.orm import selectinload
        from services.b2c.models.subscription import Subscription
        
        result = await db.execute(
            select(Workspace)
            .options(selectinload(Workspace.subscription).selectinload(Subscription.plan))
            .where(
                Workspace.owner_id == current_user['id'],
                Workspace.type == 'personal'
            )
        )
        personal_workspace = result.scalar_one_or_none()
        
        if not personal_workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Personal workspace not found"
            )
        
        # Determine subscription tier dynamically
        subscription_tier = 'free'
        if personal_workspace.subscription and personal_workspace.subscription.status in ['active', 'trialing']:
            if personal_workspace.subscription.plan:
                subscription_tier = personal_workspace.subscription.plan.tier_key
        
        # Fallback to column if relation is missing but column is set (sanity check)
        if subscription_tier == 'free' and personal_workspace.subscription_tier != 'free':
             # Note: This technically trusts the column if sub is missing/inactive, 
             # but we strictly want active subscription for features.
             # So we actually prefer the relation.
             pass
        
        # Create team workspace
        workspace = await workspace_service.create_team_workspace(
            db=db,
            name=request.name,
            owner_id=UUID(str(current_user['id'])),
            subscription_tier=subscription_tier
        )
        
        await db.commit()
        
        return {
            "id": str(workspace.id),
            "name": workspace.name,
            "type": workspace.type.value,
            "owner_id": str(workspace.owner_id),
            "subscription_tier": workspace.subscription_tier,
            "member_count": 1
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workspace: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workspace: {str(e)}"
        )


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: str,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get workspace details including members
    
    Returns workspace metadata and member list with roles
    """
    try:
        workspace_details = await workspace_service.get_workspace_details(
            db=db,
            workspace_id=UUID(workspace_id),
            user_id=UUID(str(current_user['id']))
        )
        
        return workspace_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace details"
        )


@router.patch("/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    request: UpdateWorkspaceRequest,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update workspace settings
    
    Requires owner or admin role
    """
    try:
        workspace = await workspace_service.update_workspace_settings(
            db=db,
            workspace_id=UUID(workspace_id),
            user_id=UUID(str(current_user['id'])),
            name=request.name,
            settings=request.settings
        )
        
        await db.commit()
        
        return {
            "id": str(workspace.id),
            "name": workspace.name,
            "settings": workspace.settings
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workspace: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workspace"
        )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete workspace
    
    Requires owner role
    Cascades to all members and workspace data
    Cannot delete personal workspace
    """
    try:
        await workspace_service.delete_workspace(
            db=db,
            workspace_id=UUID(workspace_id),
            user_id=UUID(str(current_user['id']))
        )
        
        await db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workspace: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workspace"
        )


# ============================================================================
# Member Management Endpoints
# ============================================================================

@router.get("/{workspace_id}/members")
async def list_members(
    workspace_id: str,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List workspace members
    
    Returns member list for workspace
    """
    try:
        workspace_details = await workspace_service.get_workspace_details(
            db=db,
            workspace_id=UUID(workspace_id),
            user_id=UUID(str(current_user['id']))
        )
        
        return {"members": workspace_details['members']}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing members: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list members"
        )


@router.patch("/{workspace_id}/members/{user_id}")
async def update_member_role(
    workspace_id: str,
    user_id: str,
    request: UpdateMemberRoleRequest,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update member role
    
    Requires owner or admin role
    Cannot change owner role
    """
    try:
        await workspace_service.update_member_role(
            db=db,
            workspace_id=UUID(workspace_id),
            target_user_id=UUID(user_id),
            new_role=request.role,
            requester_id=UUID(str(current_user['id']))
        )
        
        await db.commit()
        
        return {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role": request.role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member role: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member role"
        )



@router.patch("/{workspace_id}/members/{user_id}/status")
async def update_member_status(
    workspace_id: str,
    user_id: str,
    request: UpdateMemberStatusRequest,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update member status (active/suspended)
    
    Requires owner or admin role
    Cannot suspend owner
    """
    try:
        await workspace_service.update_member_status(
            db=db,
            workspace_id=UUID(workspace_id),
            target_user_id=UUID(user_id),
            new_status=request.status,
            requester_id=UUID(str(current_user['id']))
        )
        
        await db.commit()
        
        return {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "status": request.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member status: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member status"
        )


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove member from workspace
    
    Requires owner or admin role
    Cannot remove owner
    """
    try:
        await workspace_service.remove_member(
            db=db,
            workspace_id=UUID(workspace_id),
            target_user_id=UUID(user_id),
            requester_id=UUID(str(current_user['id']))
        )
        
        await db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing member: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member"
        )
