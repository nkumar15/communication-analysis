from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from app.db_models import UserModel
from app.models import User


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
        
        return self._model_to_pydantic(user_model)
    
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
        
        return self._model_to_pydantic(user_model)
    
    async def create_or_update_user(
        self, 
        db: AsyncSession,
        tenant_id: int, 
        email: str, 
        firebase_uid: str,
        name: Optional[str] = None,
        role: str = 'member'
    ) -> User:
        """
        Create or update user from Firebase token using UPSERT
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            email: User email
            firebase_uid: Firebase user ID
            name: User display name
            role: User role (default: member)
            
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
            role=role,
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
        
        await db.commit()
        await db.refresh(user_model)
        
        return self._model_to_pydantic(user_model)
    
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
    
    def _model_to_pydantic(self, model: UserModel) -> User:
        """Convert SQLAlchemy model to Pydantic model"""
        return User(
            id=model.id,
            tenant_id=model.tenant_id,
            email=model.email,
            name=model.name,
            firebase_uid=model.firebase_uid,
            role=model.role,
            is_active=model.is_active,
            last_login=model.last_login,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


# Global user service instance
user_service = UserService()
