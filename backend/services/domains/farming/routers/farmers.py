"""
Farmer Management API Router

CRUD endpoints for farmers with hierarchical scoping:
- Field Agent: Can only manage their own farmers
- Field Manager: Can manage farmers created by their team
- Admin: Can manage all farmers in tenant
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from core.database import get_db
from core.middleware import get_current_user
from services.b2b.rbac import require_permission
from services.domains.farming.scope_checker import (
    get_accessible_farmers_query,
    can_access_farmer
)
from services.domains.farming.models import Farmer
from services.domains.farming.schemas.farmers import FarmerCreate, FarmerUpdate, FarmerResponse

router = APIRouter(prefix="/api/b2b/farmers", tags=["farmers"])


@router.post("", response_model=FarmerResponse, status_code=status.HTTP_201_CREATED)
async def create_farmer(
    farmer_data: FarmerCreate,
    current_user: dict = require_permission('farmers', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new farmer
    
    Permission required: farmers:write
    
    The farmer will be owned by the creating user and scoped
    to their access level in the hierarchy.
    """
    # Create farmer with ownership tracking
    farmer = Farmer(
        tenant_id=current_user['tenant_id'],
        name=farmer_data.name,
        email=farmer_data.email,
        phone=farmer_data.phone,
        address=farmer_data.address,
        created_by=current_user['id']
    )
    
    db.add(farmer)
    await db.commit()
    await db.refresh(farmer)
    
    return farmer


@router.get("", response_model=List[FarmerResponse])
async def list_farmers(
    current_user: dict = require_permission('farmers', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    List all farmers accessible to current user (scoped by hierarchy)
    
    Permission required: farmers:read
    
    Scope:
    - Admin: All farmers in tenant
    - Field Manager: Farmers created by self + team
    - Field Agent: Only own farmers
    """
    # Get scoped query based on user's hierarchy
    query = await get_accessible_farmers_query(current_user['id'], db)
    
    result = await db.execute(query.order_by(Farmer.created_at.desc()))
    farmers = result.scalars().all()
    
    return farmers


@router.get("/{farmer_id}", response_model=FarmerResponse)
async def get_farmer(
    farmer_id: UUID,
    current_user: dict = require_permission('farmers', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific farmer's details
    
    Permission required: farmers:read
    
    Returns 404 if farmer doesn't exist or user doesn't have access.
    """
    # Check if user can access this farmer
    if not await can_access_farmer(current_user['id'], farmer_id, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farmer not found"
        )
    
    farmer = await db.get(Farmer, farmer_id)
    return farmer


@router.put("/{farmer_id}", response_model=FarmerResponse)
async def update_farmer(
    farmer_id: UUID,
    farmer_data: FarmerUpdate,
    current_user: dict = require_permission('farmers', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """
    Update farmer details
    
    Permission required: farmers:write
    
    Users can only update farmers they have access to based on hierarchy.
    """
    # Check access
    if not await can_access_farmer(current_user['id'], farmer_id, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farmer not found"
        )
    
    farmer = await db.get(Farmer, farmer_id)
    
    # Update provided fields
    if farmer_data.name is not None:
        farmer.name = farmer_data.name
    if farmer_data.email is not None:
        farmer.email = farmer_data.email
    if farmer_data.phone is not None:
        farmer.phone = farmer_data.phone
    if farmer_data.address is not None:
        farmer.address = farmer_data.address
    
    await db.commit()
    await db.refresh(farmer)
    
    return farmer


@router.delete("/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farmer(
    farmer_id: UUID,
    current_user: dict = require_permission('farmers', 'delete'),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a farmer
    
    Permission required: farmers:delete
    
    Users can only delete farmers they have access to based on hierarchy.
    """
    # Check access
    if not await can_access_farmer(current_user['id'], farmer_id, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farmer not found"
        )
    
    farmer = await db.get(Farmer, farmer_id)
    await db.delete(farmer)
    await db.commit()
    
    return None
