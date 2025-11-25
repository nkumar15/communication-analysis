from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from app.db_models import UserModel
from app.models import User
from app.constants import RoleName


class UserService:
    """Service for user operations using SQLAlchemy ORM"""
    
    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await db.execute(
            select(UserModel)
            .where(UserModel.id == user_id)
            .where(UserModel.is_active == True)
        )
        user_model = result.scalar_one_or_none()
        
        if not user_model:
            return None
        
        return await self._model_to_pydantic(user_model, db)
    
    async def get_user_by_firebase_uid(self, db: AsyncSession, tenant_id: int, firebase_uid: str) -> Optional[User]:
        """Get user by Firebase UID"""
        result = await db.execute(
            select(UserModel)
            .where(UserModel.tenant_id == tenant_id)
            .where(UserModel.firebase_uid == firebase_uid)
            .where(UserModel.is_active == True)
        )
        user_model = result.scalar_one_or_none()
        
        if not user_model:
            return None
        
        return await self._model_to_pydantic(user_model, db)
    
    async def create_or_update_user(
        self, 
        db: AsyncSession,
        tenant_id: int, 
        email: str, 
        firebase_uid: str,
        name: Optional[str] = None,
        role: str = RoleName.FIELD_AGENT
    ) -> User:
        """
        Create or update user from Firebase token using UPSERT
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            email: User email
            firebase_uid: Firebase user ID
            name: User display name
            role: User role (default: field_agent)
            
        Returns:
            Created or updated User
        """
        now = datetime.utcnow()
        
        # Using PostgreSQL's ON CONFLICT (UPSERT)
        stmt = insert(UserModel).values(
            tenant_id=tenant_id,
            email=email,
            name=name,
            firebase_uid=firebase_uid,
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
            from app.rbac_models import Role
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
        
        await db.commit()
        await db.refresh(user_model)
        
        return await self._model_to_pydantic(user_model, db)
    
    async def update_last_login(self, db: AsyncSession, user_id: int):
        """Update user's last login timestamp"""
        result = await db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.last_login = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            await db.commit()
    
    async def _model_to_pydantic(self, model: UserModel, db: AsyncSession = None) -> User:
        """Convert SQLAlchemy model to Pydantic model"""
        # Fetch role slug and display name if role_id is set
        role_slug = None
        role_display_name = None
        if model.role_id and db:
            from app.rbac_models import Role
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
