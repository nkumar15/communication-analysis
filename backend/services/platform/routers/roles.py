from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

from core.database import get_db
from services.platform.middleware.platform_auth import verify_platform_admin, RequirePlatformRole
from services.platform.models import PlatformRole, PlatformPermission

router = APIRouter(
    prefix="/api/platform/roles",
    tags=["platform-roles"]
)

# Schemas
class PermissionSchema(BaseModel):
    resource: str
    action: str

class RoleCreate(BaseModel):
    name: str # e.g. "audit_viewer"
    display_name: str
    description: Optional[str] = None
    permissions: List[PermissionSchema] = []

class RoleResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    description: Optional[str]
    is_system_role: bool
    permissions: List[PermissionSchema]

    class Config:
        from_attributes = True

# Endpoints
@router.get("/", response_model=List[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """List all platform roles with permissions"""
    result = await db.execute(select(PlatformRole).order_by(PlatformRole.name))
    roles = result.scalars().all()
    # Lazy loading should handle permissions due to 'selectin' in model
    return roles

@router.post("/", response_model=RoleResponse)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(RequirePlatformRole(["platform_admin"]))
):
    """Create a new custom platform role"""
    # Check duplicate
    existing = await db.scalar(select(PlatformRole).where(PlatformRole.name == role_in.name))
    if existing:
        raise HTTPException(status_code=400, detail=f"Role {role_in.name} already exists")

    new_role = PlatformRole(
        platform_tenant_id=UUID(current_user["tenant_id"]),
        name=role_in.name,
        display_name=role_in.display_name,
        description=role_in.description,
        is_system_role=False
    )
    db.add(new_role)
    await db.flush()

    for p in role_in.permissions:
        perm = PlatformPermission(
            platform_role_id=new_role.id,
            resource=p.resource,
            action=p.action
        )
        db.add(perm)

    await db.commit()
    await db.refresh(new_role)
    return new_role
