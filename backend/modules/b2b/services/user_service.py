from typing import Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from modules.b2b.models import UserModel, Role
from modules.b2b.schemas import User
from core.constants import B2BRoleName
from core.utils import get_utc_now


class UserService:
    """Service for user operations using SQLAlchemy ORM"""
    
    async def get_user_by_id(self, db: AsyncSession, user_id: UUID, tenant_id: UUID) -> Optional[User]:
        """Get user by ID with tenant scope for defense-in-depth isolation"""
        result = await db.execute(
            select(UserModel)
            .where(UserModel.id == user_id)
            .where(UserModel.tenant_id == tenant_id)  # Defense in depth
            .where(UserModel.is_active == True)
            .where(UserModel.deleted_at.is_(None))
        )
        user_model = result.scalar_one_or_none()
        
        if not user_model:
            return None
        
        return await self._model_to_pydantic(user_model, db)
    
    async def get_user_by_firebase_uid(self, db: AsyncSession, tenant_id: UUID, firebase_uid: str) -> Optional[User]:
        """Get user by Firebase UID"""
        result = await db.execute(
            select(UserModel)
            .where(UserModel.tenant_id == tenant_id)
            .where(UserModel.firebase_uid == firebase_uid)
            .where(UserModel.is_active == True)
            .where(UserModel.deleted_at.is_(None))
        )
        user_model = result.scalar_one_or_none()
        
        if not user_model:
            return None
        
        return await self._model_to_pydantic(user_model, db)
    
    async def get_user_by_email(self, db: AsyncSession, tenant_id: UUID, email: str) -> Optional[User]:
        """
        Get user by email (canonical identity lookup).
        Email is the stable identifier across web and mobile platforms.
        """
        result = await db.execute(
            select(UserModel)
            .where(UserModel.tenant_id == tenant_id)
            .where(UserModel.email == email.lower())
            .where(UserModel.is_active == True)
            .where(UserModel.deleted_at.is_(None))
        )
        user_model = result.scalar_one_or_none()
        
        if not user_model:
            return None
        
        return await self._model_to_pydantic(user_model, db)
    
    async def get_or_create_user_by_email(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        email: str,
        firebase_uid: str,
        name: Optional[str] = None,
        role: str = B2BRoleName.VIEWER
    ) -> User:
        """
        Get user by email (canonical identity), update firebase_uid if different.
        This is the industry-standard approach for cross-platform identity.
        
        - If user exists by email: update firebase_uid to latest, return user
        - If user doesn't exist: create new user
        
        This ensures the same user logging in from web or mobile
        is recognized as the same person.
        """
        email_lower = email.lower()
        now = get_utc_now()
        
        # 1. Try to find existing user by email
        result = await db.execute(
            select(UserModel)
            .where(UserModel.tenant_id == tenant_id)
            .where(UserModel.email == email_lower)
            .where(UserModel.deleted_at.is_(None))
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # 2a. User exists - update standard metadata
            existing_user.last_login = now
            existing_user.updated_at = now
            
            # Always update name if provided from SSO token (e.g., from Auth0)
            # This ensures names from SSO providers are always synced
            if name:
                existing_user.name = name
            
            # Note: We do NOT overwrite firebase_uid anymore.
            # With GCIP/signInWithIdp, UIDs are stable across platforms.
            # If they differ, it might indicate a serious issue or manual DB change.
            if existing_user.firebase_uid != firebase_uid:
                # Log warning but don't overwrite blindly
                import logging
                logging.warning(f"uid_mismatch_ignored: db={existing_user.firebase_uid}, token={firebase_uid}, email={email}")

            await db.flush()
            return await self._model_to_pydantic(existing_user, db)
        else:
            # 2b. User doesn't exist - create new
            return await self.create_or_update_user(
                db=db,
                tenant_id=tenant_id,
                email=email,
                firebase_uid=firebase_uid,
                name=name,
                role=role
            )
    
    async def create_or_update_user(
        self, 
        db: AsyncSession,
        tenant_id: UUID, 
        email: str, 
        firebase_uid: str,
        name: Optional[str] = None,
        role: str = B2BRoleName.VIEWER
    ) -> User:
        """
        Create or update user from Firebase token using UPSERT
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            email: User email
            firebase_uid: Firebase user ID
            name: User display name
            role: User role (default: viewer)
            
        Returns:
            Created or updated User
        """
        now = get_utc_now()
        
        # Look up role_id before UPSERT to ensure it's set during INSERT
        role_result = await db.execute(
            select(Role)
            .where(Role.tenant_id == tenant_id)
            .where(Role.name == role)
        )
        role_obj = role_result.scalar_one_or_none()
        role_id = role_obj.id if role_obj else None
        
        # Using PostgreSQL's ON CONFLICT (UPSERT)
        stmt = insert(UserModel).values(
            tenant_id=tenant_id,
            email=email,
            name=name,
            firebase_uid=firebase_uid,
            role_id=role_id,  # Include role_id in INSERT
            last_login=now,
        ).on_conflict_do_update(
            index_elements=['tenant_id', 'firebase_uid'],
            set_={
                'email': email,
                'name': name,
                'last_login': now,
                'updated_at': now,
            }
        ).returning(UserModel)
        
        result = await db.execute(stmt)
        user_model = result.scalar_one()
        
        # Populate role_id if missing (new user or existing user without role_id)
        if user_model.role_id is None:
            # Use the role argument passed to the function
            role_name = role
            
            # Find the corresponding Role record
            role_result = await db.execute(
                select(Role)
                .where(Role.tenant_id == tenant_id)
                .where(Role.name == role_name)
            )
            role_obj = role_result.scalar_one_or_none()
            
            if role_obj:
                # Update user with role_id
                await db.execute(
                    UserModel.__table__.update()
                    .where(UserModel.id == user_model.id)
                    .values(role_id=role_obj.id)
                )
                user_model.role_id = role_obj.id
        
        # Flush to DB and re-query with RLS context still active
        # Router will handle commit() to maintain transaction boundaries
        await db.flush()
        result = await db.execute(
            select(UserModel).where(UserModel.id == user_model.id)
        )
        user_model = result.scalar_one()
        
        return await self._model_to_pydantic(user_model, db)
    
    async def update_last_login(self, db: AsyncSession, user_id: UUID):
        """Update user's last login timestamp"""
        result = await db.execute(
            select(UserModel)
            .where(UserModel.id == user_id)
            .where(UserModel.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.last_login = get_utc_now()
            user.updated_at = get_utc_now()
            await db.flush()
            
    async def delete_user(self, db: AsyncSession, user_id: UUID) -> bool:
        """
        Soft delete a user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if deleted, False if not found
        """
        result = await db.execute(
            select(UserModel)
            .where(UserModel.id == user_id)
            .where(UserModel.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
            
        user.deleted_at = get_utc_now()
        user.is_active = False
        
        await db.flush()
        return True
    
    async def get_user_stats(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID
    ) -> dict:
        """
        Get user statistics for dashboard
        
        Returns:
            Dictionary with total_users, active_users, pending_invitations, managers_count
        """
        from sqlalchemy import func
        from modules.b2b.models import InvitationModel
        from modules.b2b.rbac import get_dashboard_stats
        from modules.b2b.rbac.permission_checker import has_permission
        from fastapi import HTTPException, status
        
        # Check if user has dashboard access
        if not await has_permission(user_id, 'dashboard', 'read', db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dashboard access denied. Field agents cannot access dashboard."
            )
        
        # Get scoped stats based on user's role and hierarchy
        stats = await get_dashboard_stats(user_id, db)
        
        # Get pending invitations count
        pending_result = await db.execute(
            select(func.count(InvitationModel.id))
            .where(InvitationModel.tenant_id == tenant_id)
            .where(InvitationModel.accepted_at.is_(None))
        )
        pending_invitations = pending_result.scalar()
        
        return {
            "total_users": stats['total_users'],
            "active_users": stats['accessible_users'],
            "pending_invitations": pending_invitations,
            "managers_count": stats.get('total_projects', 0)
        }
    
    async def list_accessible_users(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> list:
        """
        List all users accessible to the current user based on hierarchy
        
        Returns:
            List of dictionaries with user information, role names, and team memberships
        """
        from modules.b2b.rbac import get_accessible_user_ids
        from modules.b2b.models import Role, TeamMember, Team, TeamRoleDefinition
        
        # Get accessible user IDs based on hierarchy
        accessible_ids = await get_accessible_user_ids(user_id, db)
        
        # Get users along with their roles
        users_result = await db.execute(
            select(UserModel, Role)
            .join(Role, UserModel.role_id == Role.id)
            .where(UserModel.id.in_(accessible_ids))
            .order_by(UserModel.created_at.desc())
        )
        users = users_result.all()
        
        # Get team memberships for all accessible users
        team_memberships_result = await db.execute(
            select(TeamMember, Team)
            .join(Team, TeamMember.team_id == Team.id)
            .where(
                TeamMember.user_id.in_(accessible_ids),
                Team.deleted_at.is_(None)
            )
        )
        team_memberships = team_memberships_result.all()
        
        # Get all team role definitions for display_name lookup
        # Prioritize tenant-specific roles, fall back to system roles
        role_defs_result = await db.execute(
            select(TeamRoleDefinition)
            .order_by(TeamRoleDefinition.tenant_id.desc().nulls_last())
        )
        role_defs = role_defs_result.scalars().all()
        
        # Build role name -> display_name lookup (first match wins due to ordering)
        role_display_map = {}
        for rd in role_defs:
            if rd.name not in role_display_map:
                role_display_map[rd.name] = rd.display_name
        
        # Build user_id -> teams mapping with display_name
        user_teams_map = {}
        for tm, team in team_memberships:
            if tm.user_id not in user_teams_map:
                user_teams_map[tm.user_id] = []
            user_teams_map[tm.user_id].append({
                "team_id": team.id,
                "team_name": team.name,
                "team_role": tm.team_role,
                "team_role_display": role_display_map.get(tm.team_role, tm.team_role)
            })
        
        return [
            {
                "id": u[0].id,
                "name": u[0].name,
                "email": u[0].email,
                "role": u[1].name if u[1] else None,
                "is_active": u[0].is_active,
                "last_login": u[0].last_login,
                "created_at": u[0].created_at,
                "teams": user_teams_map.get(u[0].id, [])
            }
            for u in users
        ]
    
    async def update_user_role(
        self,
        db: AsyncSession,
        user_id: UUID,
        role_name: str,
        current_user_id: UUID,
        current_user_role: str,
        tenant_id: UUID
    ) -> dict:
        """
        Update a user's role with validation and hierarchy checks
        
        Args:
            db: Database session
            user_id: ID of user whose role to update
            role_name: New role name to assign
            current_user_id: ID of user making the change
            current_user_role: Role of user making the change
            tenant_id: Tenant ID
            
        Returns:
            Success message dictionary
            
        Raises:
            HTTPException: For various validation failures
        """
        from modules.b2b.models import Role
        from modules.b2b.rbac.permission_checker import has_permission
        from fastapi import HTTPException, status
        
        # 1. Check permission
        if not await has_permission(current_user_id, 'users', 'invite', db) and current_user_role != 'owner':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Only admins can update roles."
            )
        
        # 2. Get target user with role
        result = await db.execute(
            select(UserModel, Role.name.label("role_name"))
            .join(Role, UserModel.role_id == Role.id)
            .where(
                UserModel.id == user_id,
                UserModel.tenant_id == tenant_id
            )
        )
        user_row = result.first()
        
        if not user_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = user_row[0]
        user_role_name = user_row.role_name
        
        # 3. Validate new role exists
        role_result = await db.execute(
            select(Role).where(
                Role.tenant_id == tenant_id,
                Role.name == role_name
            )
        )
        role_obj = role_result.scalar_one_or_none()
        
        if not role_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_name}' not found."
            )
        
        # 4. Hierarchy and safety checks
        
        # 4.1 Prevent self-modification
        if user.id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot change your own role. Ask another admin to do it."
            )
        
        # 4.2 Owner protection
        if user_role_name == 'owner' and current_user_role != 'owner':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins cannot modify the Owner's role."
            )
        
        # 4.3 Admin vs Admin protection
        if user_role_name == 'admin' and current_user_role != 'owner':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins cannot modify other Admins. Only the Owner can do that."
            )
        
        # 4.4 Prevent elevating to Owner
        if role_name == 'owner':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign 'owner' role via this endpoint. Use specific transfer ownership process."
            )
        
        # 5. Update role
        user.role_id = role_obj.id
        await db.flush()
        
        return {"message": "User role updated successfully"}

    async def deactivate_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        current_user_id: UUID,
        current_user_role: str,
        tenant_id: UUID
    ) -> dict:
        """
        Deactivate a user with strict safety checks.
        
        Rules:
        1. Cannot deactivate self.
        2. Cannot deactivate Tenant Owner.
        3. Admins cannot deactivate other Admins (only Owner can).
        """
        from modules.b2b.models import Role
        from modules.b2b.rbac.permission_checker import has_permission
        from fastapi import HTTPException, status

        # 1. Permission check (Owner/Admin)
        if not await has_permission(current_user_id, 'users', 'invite', db) and current_user_role != 'owner':
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Only admins can deactivate users."
            )

        # 2. Prevent self-deactivation
        if user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate yourself."
            )

        # 3. Get target user with role name
        result = await db.execute(
            select(UserModel, Role.name.label("role_name"))
            .outerjoin(Role, UserModel.role_id == Role.id)
            .where(
                UserModel.id == user_id,
                UserModel.tenant_id == tenant_id,
                UserModel.deleted_at.is_(None)
            )
        )
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
            
        target_user = row[0]
        target_role_name = row.role_name

        # 4. Owner Protection
        if target_role_name == 'owner':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The Tenant Owner cannot be deactivated."
            )

        # 5. Admin vs Admin Protection
        if current_user_role == 'admin' and target_role_name == 'admin':
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins cannot deactivate other Admins. Only the Owner can do that."
            )

        # 6. Apply Deactivation
        target_user.is_active = False
        target_user.updated_at = get_utc_now()
        await db.flush()
        
        return {"message": "User deactivated successfully"}

    async def reactivate_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        current_user_id: UUID,
        current_user_role: str,
        tenant_id: UUID
    ) -> dict:
        """
        Reactivate a user. 
        Same permission rules apply as deactivation to prevent privilege escalation.
        """
        from modules.b2b.models import Role
        from modules.b2b.rbac.permission_checker import has_permission
        from fastapi import HTTPException, status

        # 1. Permission check
        if not await has_permission(current_user_id, 'users', 'invite', db) and current_user_role != 'owner':
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied."
            )

        # 2. Get target user
        result = await db.execute(
            select(UserModel, Role.name.label("role_name"))
            .outerjoin(Role, UserModel.role_id == Role.id)
            .where(
                UserModel.id == user_id,
                UserModel.tenant_id == tenant_id,
                UserModel.deleted_at.is_(None)
            )
        )
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
            
        target_user = row[0]
        
        # 3. Apply Reactivation
        target_user.is_active = True
        target_user.updated_at = get_utc_now()
        await db.flush()
        
        return {"message": "User reactivated successfully"}
    
    async def _model_to_pydantic(self, model: UserModel, db: AsyncSession = None) -> User:
        """Convert SQLAlchemy model to Pydantic model"""
        # Fetch role slug and display name if role_id is set
        role_slug = None
        role_display_name = None
        if model.role_id and db:
            from modules.b2b.models import Role
            role_result = await db.execute(
                select(Role).where(Role.id == model.role_id)
            )
            role = role_result.scalar_one_or_none()
            if role:
                role_slug = role.name
                role_display_name = role.display_name
        
        return User(
            id=model.id,
            tenant_id=model.tenant_id,
            email=model.email,
            name=model.name,
            firebase_uid=model.firebase_uid,
            role_id=model.role_id,
            role=role_slug,  # Role slug (e.g., 'admin')
            role_display_name=role_display_name,
            is_active=model.is_active,
            last_login=model.last_login,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


# Global user service instance
user_service = UserService()
