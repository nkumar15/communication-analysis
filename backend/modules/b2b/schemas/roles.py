from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from typing import List, Optional


class ResourceResponse(BaseModel):
    """Resource information"""
    id: UUID
    name: str
    display_name: str
    category: Optional[str]
    description: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class ActionResponse(BaseModel):
    """Action information"""
    id: UUID
    name: str
    display_name: str
    description: Optional[str] = None
    applicable_resources: Optional[List[str]] = None  # null = applies to all
    
    model_config = ConfigDict(from_attributes=True)


class PermissionResponse(BaseModel):
    """Permission details"""
    resource: ResourceResponse
    action: ActionResponse
    
    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    """Request schema for creating a new role"""
    name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    template_id: Optional[UUID] = None
    permissions: List[dict] = []


class RoleUpdate(BaseModel):
    """Request schema for updating a role"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[dict]] = None


class RoleResponse(BaseModel):
    """Response schema for role"""
    id: UUID
    tenant_id: UUID
    name: str
    display_name: str
    description: Optional[str] = None
    is_system_role: bool
    permissions: List[PermissionResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class RoleTemplateResponse(BaseModel):
    """Response schema for role templates"""
    id: UUID
    name: str
    display_name: str
    description: Optional[str] = None
    permissions: List[dict] = []
    is_system_role: bool
    
    model_config = ConfigDict(from_attributes=True)


class RoleDetailResponse(BaseModel):
    """Role with full permission details"""
    id: UUID
    name: str
    display_name: str
    description: Optional[str]
    is_system_role: bool
    is_active: bool
    permissions: list[PermissionResponse]
    
    model_config = ConfigDict(from_attributes=True)


class UpdateRolePermissionsRequest(BaseModel):
    """Request to update role permissions"""
    permissions: list[dict]  # [{"resource_id": 1, "action_id": 1}, ...]
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "permissions": [
                    {"resource_id": 1, "action_id": 1},
                    {"resource_id": 1, "action_id": 2},
                    {"resource_id": 2, "action_id": 1}
                ]
            }
        }
    )


class CreateRoleRequest(BaseModel):
    """Request to create a new role"""
    name: str
    display_name: str
    description: Optional[str] = None
    template_id: Optional[UUID] = None
    permissions: Optional[list[dict]] = None  # [{"resource_id": "...", "action_id": "..."}]
