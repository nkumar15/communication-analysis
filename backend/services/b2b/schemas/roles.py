"""
Pydantic schemas for Role Management API
"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class ResourceResponse(BaseModel):
    """Resource information"""
    id: UUID
    name: str
    display_name: str
    category: Optional[str]
    description: Optional[str]
    
    class Config:
        from_attributes = True


class ActionResponse(BaseModel):
    """Action information"""
    id: UUID
    name: str
    display_name: str
    
    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    """Permission details"""
    resource: ResourceResponse
    action: ActionResponse
    
    class Config:
        from_attributes = True


class RoleTemplateResponse(BaseModel):
    """Role template information"""
    id: UUID
    name: str
    display_name: str
    description: Optional[str]
    is_system_role: bool
    is_default: bool
    permissions: list[dict]

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    """Role with basic information"""
    id: UUID
    name: str
    display_name: str
    description: Optional[str]
    is_system_role: bool
    is_active: bool
    
    class Config:
        from_attributes = True


class RoleDetailResponse(BaseModel):
    """Role with full permission details"""
    id: UUID
    name: str
    display_name: str
    description: Optional[str]
    is_system_role: bool
    is_active: bool
    permissions: list[PermissionResponse]
    
    class Config:
        from_attributes = True


class UpdateRolePermissionsRequest(BaseModel):
    """Request to update role permissions"""
    permissions: list[dict]  # [{"resource_id": 1, "action_id": 1}, ...]
    
    class Config:
        json_schema_extra = {
            "example": {
                "permissions": [
                    {"resource_id": 1, "action_id": 1},
                    {"resource_id": 1, "action_id": 2},
                    {"resource_id": 2, "action_id": 1}
                ]
            }
        }


class CreateRoleRequest(BaseModel):
    """Request to create a new role"""
    name: str
    display_name: str
    description: Optional[str] = None
    template_id: Optional[UUID] = None
    permissions: Optional[list[dict]] = None  # [{"resource_id": "...", "action_id": "..."}]
