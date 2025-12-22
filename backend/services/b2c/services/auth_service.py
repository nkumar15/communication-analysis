"""B2C Authentication Service"""
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from uuid import uuid4

from infrastructure.auth import firebase_auth_service
from services.b2c.models.user import B2CUser
from services.b2c.models.workspace import Workspace, WorkspaceType
from services.b2c.models.workspace_member import WorkspaceMember
from services.b2c.models.workspace_member import WorkspaceMember
from core.logging import get_logger
from core.rls import rls_service

logger = get_logger(__name__)


class AuthService:
    """B2C Authentication Service"""
    
    async def signup(
        self,
        db: AsyncSession,
        firebase_uid: str,
        email: str,
        display_name: Optional[str] = None,
        email_verified: bool = False
    ) -> Dict:
        """
        Sign up new B2C user
        
        Creates:
        - User record
        - Personal workspace (auto-created)
        - Workspace membership (owner)
        
        Returns user and workspace data
        """
        # Check if user already exists using Security Definer lookup (RLS safe)
        from sqlalchemy import func, text
        existing_user_id = await db.scalar(
            select(func.b2c.lookup_user_by_firebase_uid(firebase_uid))
        )
        
        if existing_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )
        

        
        # Require email verification for signup
        if not email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email must be verified before signup"
            )
        
        # Pre-generate user ID so we can set RLS context
        user_id = uuid4()
        
        # Set RLS context to this user to allow creation
        await rls_service.set_user_context(db, str(user_id))
        
        # Create user
        user = B2CUser(
            id=user_id,
            firebase_uid=firebase_uid,
            email=email,
            display_name=display_name or email.split('@')[0]
        )
        db.add(user)
        await db.flush()
        
        # Create personal workspace
        workspace = Workspace(
            name=f"{user.display_name}'s Workspace",
            type=WorkspaceType.personal,
            owner_id=user.id,
            subscription_tier='free'
        )
        db.add(workspace)
        await db.flush()
        
        # Link user to personal workspace
        user.default_workspace_id = workspace.id
        
        # Add user as workspace member (owner)
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role='owner'
        )
        db.add(member)
        
        
        # NOTE: We do NOT commit here to preserve RLS context (SET LOCAL is transaction scoped)
        # and to allow test transaction isolation.
        await db.flush()
        await db.refresh(user)
        await db.refresh(workspace)
        
        logger.info(
            "b2c_user_signup",
            user_id=str(user.id),
            email=user.email,
            workspace_id=str(workspace.id)
        )
        
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "personal_workspace_id": str(workspace.id)
            },
            "workspace": {
                "id": str(workspace.id),
                "name": workspace.name,
                "type": workspace.type.value
            }
        }
    
    async def get_or_create_user(
        self,
        db: AsyncSession,
        firebase_uid: str,
        email: str,
        display_name: Optional[str] = None,
        email_verified: bool = False
    ) -> B2CUser:
        """
        Get existing user or create new one (idempotent login)
        
        Used for login flow - if user exists, return it
        If not (first-time Google login), create user + workspace
        """
        # Try to find existing user using SECURITY DEFINER function to bypass RLS
        # We can't query the table directly because RLS requires us to set the user ID first,
        # but we don't know the user ID yet!
        
        user_id = await db.scalar(
            select(func.b2c.lookup_user_by_firebase_uid(firebase_uid))
        )
        
        if user_id:
            # Found user! Set RLS context using centralized service
            await rls_service.set_user_context(db, str(user_id))
            
            # Now we can fetch the user details safely
            user = await db.scalar(
                select(B2CUser).where(B2CUser.id == user_id)
            )
            
            # Update last login
            from datetime import datetime, timezone
            user.last_login_at = datetime.now(timezone.utc)
            await db.flush()
            return user
        
        # First time login - create user via signup
        result = await self.signup(
            db, firebase_uid, email, display_name, email_verified
        )
        
        # Fetch created user
        user = await db.scalar(
            select(B2CUser).where(B2CUser.firebase_uid == firebase_uid)
        )
        return user
    
    async def get_user_workspaces(
        self,
        db: AsyncSession,
        user_id: str
    ) -> list:
        """Get all workspaces user has access to"""
        from sqlalchemy.orm import selectinload
        from uuid import UUID
        
        # Convert string to UUID
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        
        # Get workspace memberships with workspace details
        result = await db.execute(
            select(WorkspaceMember)
            .where(WorkspaceMember.user_id == user_uuid)
            .options(selectinload(WorkspaceMember.workspace))
        )
        memberships = result.scalars().all()
        
        workspaces = []
        for membership in memberships:
            if membership.workspace:
                workspaces.append({
                    "id": str(membership.workspace.id),
                    "name": membership.workspace.name,
                    "type": membership.workspace.type.value,
                    "role": membership.role
                })
        
        return workspaces


# Singleton instance
auth_service = AuthService()
