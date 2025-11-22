from typing import Optional, Dict, Any
from datetime import datetime
from app.database import db
from app.models import User


class UserService:
    """Service for user operations"""
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        query = """
            SELECT id, tenant_id, email, name, external_id, is_active, 
                   last_login, created_at, updated_at
            FROM users
            WHERE id = $1 AND is_active = TRUE
        """
        
        row = await db.fetchrow(query, user_id)
        
        if not row:
            return None
        
        return User(**dict(row))
    
    async def get_user_by_firebase_uid(self, tenant_id: int, firebase_uid: str) -> Optional[User]:
        """Get user by Firebase UID"""
        query = """
            SELECT id, tenant_id, email, name, firebase_uid, is_active,
                   last_login, created_at, updated_at
            FROM users
            WHERE tenant_id = $1 AND firebase_uid = $2 AND is_active = TRUE
        """
        
        row = await db.fetchrow(query, tenant_id, firebase_uid)
        
        if not row:
            return None
        
        return User(**dict(row))
    
    async def create_or_update_user(
        self, 
        tenant_id: int, 
        email: str, 
        firebase_uid: str,
        name: Optional[str] = None
    ) -> User:
        """
        Create or update user from Firebase token
        
        Args:
            tenant_id: Tenant ID
            email: User email
            firebase_uid: Firebase user ID
            name: User display name
            
        Returns:
            Created or updated User
        """
        query = """
            INSERT INTO users (tenant_id, email, name, firebase_uid, last_login)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (tenant_id, firebase_uid)
            DO UPDATE SET
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                last_login = EXCLUDED.last_login,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, tenant_id, email, name, firebase_uid, is_active,
                      last_login, created_at, updated_at
        """
        
        now = datetime.utcnow()
        row = await db.fetchrow(query, tenant_id, email, name, firebase_uid, now)
        
        return User(**dict(row))
    
    async def update_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        query = """
            UPDATE users
            SET last_login = $1, updated_at = $1
            WHERE id = $2
        """
        
        await db.execute(query, datetime.utcnow(), user_id)


# Global user service instance
user_service = UserService()
