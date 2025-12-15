from sqlalchemy import Column, String, UUID, DateTime, text, ForeignKey, Boolean
from core.models.base import Base, TimestampMixin

class B2CUser(Base, TimestampMixin):
    """
    B2C User model
    
    Separate from B2B tenant users. Each B2C user can have multiple workspaces.
    """
    __tablename__ = "users"
    __table_args__ = {'schema': 'b2c'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    firebase_uid = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255))
    avatar_url = Column(String(500))
    email_verified = Column(Boolean, default=False)
    default_workspace_id = Column(UUID(as_uuid=True), ForeignKey('b2c.workspaces.id'))
    
    last_login_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
