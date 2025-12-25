"""
B2C Invitations Router

Endpoints for workspace invitation management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

from core.db.session import get_db
from modules.b2c.middleware.b2c_auth import get_current_b2c_user
from modules.b2c.services.invitation_service import invitation_service
from modules.b2c.services.workspace_service import workspace_service
from infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/b2c", tags=["B2C Invitations"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str = 'member'  # admin, member, viewer


# ============================================================================
# Invitation Endpoints
# ============================================================================

@router.post("/workspaces/{workspace_id}/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    workspace_id: str,
    request: InviteUserRequest,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Invite user to workspace by email
    
    Requires owner or admin role
    Sends invitation email with acceptance link
    """
    try:
        invitation = await invitation_service.invite_user(
            db=db,
            workspace_id=UUID(workspace_id),
            email=request.email,
            role=request.role,
            inviter_id=UUID(str(current_user['id'])),
            inviter_name=current_user.get('display_name') or current_user.get('email')
        )
        
        await db.commit()
        
        return {
            "id": str(invitation.id),
            "workspace_id": workspace_id,
            "email": invitation.email,
            "role": invitation.role,
            "invitation_token": invitation.invitation_token,
            "expires_at": invitation.expires_at.isoformat(),
            "message": "Invitation created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating invitation: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create invitation: {str(e)}"
        )





@router.get("/workspaces/{workspace_id}/invitations")
async def list_pending_invitations(
    workspace_id: str,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List pending invitations for workspace
    
    Requires owner or admin role
    """
    try:
        from core.db.rls import rls_service
        
        # Set RLS context
        await rls_service.set_user_context(db, str(current_user['id']))
        
        # Check permission
        await workspace_service.verify_workspace_access(
            db, UUID(workspace_id), UUID(str(current_user['id'])), min_role='admin'
        )
        
        invitations = await invitation_service.get_pending_invitations(
            db=db,
            workspace_id=UUID(workspace_id)
        )
        
        return {"invitations": invitations}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing invitations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list invitations"
        )
@router.get("/invitations/{token}")
async def get_invitation(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get invitation details by token
    
    Public endpoint - no authentication required
    Used to display invitation details before acceptance
    """
    try:
        from core.db.rls import rls_service
        
        # Set platform admin context to bypass RLS for public invitation lookup
        await rls_service.set_platform_admin_context(db)
        
        invitation_details = await invitation_service.get_invitation_by_token(
            db=db,
            token=token
        )
        
        return invitation_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invitation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get invitation details"
        )


@router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept workspace invitation
    
    Requires authentication
    User's email must match invitation email
    Adds user as workspace member
    """
    try:
        from core.db.rls import rls_service
        
        # Set RLS context
        await rls_service.set_user_context(db, str(current_user['id']))
        
        result = await invitation_service.accept_invitation(
            db=db,
            token=token,
            user_id=UUID(str(current_user['id']))
        )
        
        await db.commit()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting invitation: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept invitation: {str(e)}"
        )


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    invitation_id: str,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel/delete invitation
    
    Only inviter or workspace admin/owner can cancel
    """
    try:
        from core.db.rls import rls_service
        
        # Set RLS context
        await rls_service.set_user_context(db, str(current_user['id']))
        
        await invitation_service.cancel_invitation(
            db=db,
            invitation_id=UUID(invitation_id),
            requester_id=UUID(str(current_user['id']))
        )
        
        await db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling invitation: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel invitation"
        )



@router.post("/invitations/{invitation_id}/resend")
async def resend_invitation(
    invitation_id: str,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resend invitation email
    
    Extends expiry and sends new email
    Only inviter or workspace admin/owner
    """
    try:
        from core.db.rls import rls_service
        
        # Set RLS context
        await rls_service.set_user_context(db, str(current_user['id']))
        
        invitation = await invitation_service.resend_invitation(
            db=db,
            invitation_id=UUID(invitation_id),
            requester_id=UUID(str(current_user['id'])),
            requester_name=current_user.get('display_name') or current_user.get('email')
        )
        
        await db.commit()
        
        return {
            "id": str(invitation.id),
            "expires_at": invitation.expires_at.isoformat(),
            "message": "Invitation resent successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending invitation: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend invitation"
        )
