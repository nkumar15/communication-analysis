"""
Pydantic schemas for Role Management API
"""
from pydantic import BaseModel
from typing import Optional


class ResourceResponse(BaseModel):
    """Resource information"""
    id: int
    name: str
    display_name: str
    category: Optional[str]
    description: Optional[str]
    
    class Config:
        from_attributes = True


class ActionResponse(BaseModel):
    """Action information"""
    id: int
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


class RoleResponse(BaseModel):
    """Role with basic information"""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    is_system_role: bool
    is_active: bool
    
    class Config:
        from_attributes = True


class RoleDetailResponse(BaseModel):
    """Role with full permission details"""
    id: int
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
