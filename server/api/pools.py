"""
Pool Management API endpoints for the Pacman Sync Utility.

This module implements FastAPI endpoints for pool CRUD operations,
endpoint assignment, and pool status retrieval with comprehensive
input validation and error handling.
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, validator

from shared.models import PackagePool, SyncPolicy, ConflictResolution
from server.core.pool_manager import PackagePoolManager, PoolStatusInfo
from server.database.orm import ValidationError, NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class SyncPolicyRequest(BaseModel):
    """Request model for sync policy configuration."""
    auto_sync: bool = False
    exclude_packages: List[str] = Field(default_factory=list)
    include_aur: bool = False
    conflict_resolution: str = Field(default="manual", pattern="^(manual|newest|oldest)$")
    
    @validator('exclude_packages')
    def validate_exclude_packages(cls, v):
        if not isinstance(v, list):
            raise ValueError('exclude_packages must be a list')
        return [pkg.strip() for pkg in v if pkg.strip()]


class CreatePoolRequest(BaseModel):
    """Request model for creating a new pool."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=1000)
    sync_policy: Optional[SyncPolicyRequest] = None
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Pool name cannot be empty')
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        return v.strip() if v else ""


class UpdatePoolRequest(BaseModel):
    """Request model for updating a pool."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    sync_policy: Optional[SyncPolicyRequest] = None
    target_state_id: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Pool name cannot be empty')
        return v.strip() if v else None
    
    @validator('description')
    def validate_description(cls, v):
        return v.strip() if v else None


class PoolResponse(BaseModel):
    """Response model for pool information."""
    id: str
    name: str
    description: str
    endpoints: List[str]
    target_state_id: Optional[str]
    sync_policy: dict
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_pool(cls, pool: PackagePool) -> "PoolResponse":
        return cls(
            id=pool.id,
            name=pool.name,
            description=pool.description,
            endpoints=pool.endpoints,
            target_state_id=pool.target_state_id,
            sync_policy=pool.sync_policy.to_dict(),
            created_at=pool.created_at,
            updated_at=pool.updated_at
        )


class PoolStatusResponse(BaseModel):
    """Response model for pool status information."""
    pool_id: str
    pool_name: str
    total_endpoints: int
    in_sync_count: int
    ahead_count: int
    behind_count: int
    offline_count: int
    sync_percentage: float
    overall_status: str
    has_target_state: bool
    auto_sync_enabled: bool
    
    @classmethod
    def from_status_info(cls, status_info: PoolStatusInfo) -> "PoolStatusResponse":
        status_dict = status_info.to_dict()
        return cls(**status_dict)


class AssignEndpointRequest(BaseModel):
    """Request model for assigning an endpoint to a pool."""
    endpoint_id: str = Field(..., min_length=1)
    
    @validator('endpoint_id')
    def validate_endpoint_id(cls, v):
        if not v.strip():
            raise ValueError('Endpoint ID cannot be empty')
        return v.strip()


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: dict


# Dependency to get pool manager
async def get_pool_manager(request: Request) -> PackagePoolManager:
    """Get pool manager from app state."""
    return request.app.state.pool_manager


# Pool CRUD Endpoints
@router.post("/pools", response_model=PoolResponse, status_code=201)
async def create_pool(
    pool_request: CreatePoolRequest,
    pool_manager: PackagePoolManager = Depends(get_pool_manager)
):
    """
    Create a new package pool.
    
    Creates a new pool with the specified name, description, and sync policy.
    Pool names must be unique across the system.
    """
    logger.info(f"Creating pool: {pool_request.name}")
    
    try:
        # Convert sync policy if provided
        sync_policy = None
        if pool_request.sync_policy:
            sync_policy = SyncPolicy(
                auto_sync=pool_request.sync_policy.auto_sync,
                exclude_packages=pool_request.sync_policy.exclude_packages,
                include_aur=pool_request.sync_policy.include_aur,
                conflict_resolution=ConflictResolution(pool_request.sync_policy.conflict_resolution)
            )
        
        # Create the pool
        pool = await pool_manager.create_pool(
            name=pool_request.name,
            description=pool_request.description,
            sync_policy=sync_policy
        )
        
        logger.info(f"Successfully created pool: {pool.id}")
        return PoolResponse.from_pool(pool)
        
    except ValidationError as e:
        logger.warning(f"Validation error creating pool: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating pool: {e}")
        raise HTTPException(status_code=500, detail="Failed to create pool")


@router.get("/pools", response_model=List[PoolResponse])
async def list_pools(
    pool_manager: PackagePoolManager = Depends(get_pool_manager)
):
    """
    List all package pools.
    
    Returns a list of all pools in the system with their current configuration
    and assigned endpoints.
    """
    logger.debug("Listing all pools")
    
    try:
        pools = await pool_manager.list_pools()
        return [PoolResponse.from_pool(pool) for pool in pools]
        
    except Exception as e:
        logger.error(f"Error listing pools: {e}")
        raise HTTPException(status_code=500, detail="Failed to list pools")


@router.get("/pools/{pool_id}", response_model=PoolResponse)
async def get_pool(
    pool_id: str,
    pool_manager: PackagePoolManager = Depends(get_pool_manager)
):
    """
    Get a specific pool by ID.
    
    Returns detailed information about a pool including its configuration,
    assigned endpoints, and current status.
    """
    logger.debug(f"Getting pool: {pool_id}")
    
    try:
        pool = await pool_manager.get_pool(pool_id)
        if not pool:
            raise HTTPException(status_code=404, detail=f"Pool {pool_id} not found")
        
        return PoolResponse.from_pool(pool)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pool")


@router.put("/pools/{pool_id}", response_model=PoolResponse)
async def update_pool(
    pool_id: str,
    pool_request: UpdatePoolRequest,
    pool_manager: PackagePoolManager = Depends(get_pool_manager)
):
    """
    Update a pool's configuration.
    
    Updates the specified pool with new name, description, sync policy,
    or target state. Only provided fields will be updated.
    """
    logger.info(f"Updating pool: {pool_id}")
    
    try:
        # Prepare update data
        update_data = {}
        
        if pool_request.name is not None:
            update_data['name'] = pool_request.name
        
        if pool_request.description is not None:
            update_data['description'] = pool_request.description
        
        if pool_request.sync_policy is not None:
            update_data['sync_policy'] = SyncPolicy(
                auto_sync=pool_request.sync_policy.auto_sync,
                exclude_packages=pool_request.sync_policy.exclude_packages,
                include_aur=pool_request.sync_policy.include_aur,
                conflict_resolution=ConflictResolution(pool_request.sync_policy.conflict_resolution)
            )
        
        if pool_request.target_state_id is not None:
            update_data['target_state_id'] = pool_request.target_state_id
        
        # Update the pool
        pool = await pool_manager.update_pool(pool_id, **update_data)
        
        logger.info(f"Successfully updated pool: {pool_id}")
        return PoolResponse.from_pool(pool)
        
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Pool {pool_id} not found")
    except ValidationError as e:
        logger.warning(f"Validation error updating pool {pool_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update pool")


@router.delete("/pools/{pool_id}", status_code=204)
async def delete_pool(
    pool_id: str,
    pool_manager: PackagePoolManager = Depends(get_pool_manager)
):
    """
    Delete a pool.
    
    Deletes the specified pool and removes all endpoint assignments.
    This operation cannot be undone.
    """
    logger.info(f"Deleting pool: {pool_id}")
    
    try:
        success = await pool_manager.delete_pool(pool_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Pool {pool_id} not found")
        
        logger.info(f"Successfully deleted pool: {pool_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete pool")


# Pool Status Endpoints
@router.get("/pools/{pool_id}/status", response_model=PoolStatusResponse)
async def get_pool_status(
    pool_id: str,
    pool_manager: PackagePoolManager = Depends(get_pool_manager)
):
    """
    Get detailed status information for a pool.
    
    Returns comprehensive status information including endpoint counts,
    sync percentages, and overall pool health.
    """
    logger.debug(f"Getting status for pool: {pool_id}")
    
    try:
        status_info = await pool_manager.get_pool_status(pool_id)
        if not status_info:
            raise HTTPException(status_code=404, detail=f"Pool {pool_id} not found")
        
        return PoolStatusResponse.from_status_info(status_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pool status {pool_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pool status")


@router.get("/pools/status", response_model=List[PoolStatusResponse])
async def list_pool_statuses(
    pool_manager: PackagePoolManager = Depends(get_pool_manager)
):
    """
    Get status information for all pools.
    
    Returns status information for all pools in the system, useful for
    dashboard displays and monitoring.
    """
    logger.debug("Getting status for all pools")
    
    try:
        status_infos = await pool_manager.list_pool_statuses()
        return [PoolStatusResponse.from_status_info(info) for info in status_infos]
        
    except Exception as e:
        logger.error(f"Error listing pool statuses: {e}")
        raise HTTPException(status_code=500, detail="Failed to list pool statuses")


# Endpoint Assignment Endpoints
@router.post("/pools/{pool_id}/endpoints", status_code=204)
async def assign_endpoint_to_pool(
    pool_id: str,
    assignment_request: AssignEndpointRequest,
    pool_manager: PackagePoolManager = Depends(get_pool_manager)
):
    """
    Assign an endpoint to a pool.
    
    Assigns the specified endpoint to the pool. If the endpoint is already
    assigned to another pool, it will be moved to the new pool.
    """
    logger.info(f"Assigning endpoint {assignment_request.endpoint_id} to pool {pool_id}")
    
    try:
        success = await pool_manager.assign_endpoint(pool_id, assignment_request.endpoint_id)
        if not success:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to assign endpoint {assignment_request.endpoint_id} to pool {pool_id}"
            )
        
        logger.info(f"Successfully assigned endpoint {assignment_request.endpoint_id} to pool {pool_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning endpoint to pool: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign endpoint to pool")


@router.delete("/pools/{pool_id}/endpoints/{endpoint_id}", status_code=204)
async def remove_endpoint_from_pool(
    pool_id: str,
    endpoint_id: str,
    pool_manager: PackagePoolManager = Depends(get_pool_manager)
):
    """
    Remove an endpoint from a pool.
    
    Removes the specified endpoint from the pool, making it unassigned.
    The endpoint will remain registered but won't participate in pool synchronization.
    """
    logger.info(f"Removing endpoint {endpoint_id} from pool {pool_id}")
    
    try:
        success = await pool_manager.remove_endpoint(pool_id, endpoint_id)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to remove endpoint {endpoint_id} from pool {pool_id}"
            )
        
        logger.info(f"Successfully removed endpoint {endpoint_id} from pool {pool_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing endpoint from pool: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove endpoint from pool")


@router.put("/pools/{pool_id}/endpoints/{endpoint_id}/move/{target_pool_id}", status_code=204)
async def move_endpoint_between_pools(
    pool_id: str,
    endpoint_id: str,
    target_pool_id: str,
    pool_manager: PackagePoolManager = Depends(get_pool_manager)
):
    """
    Move an endpoint from one pool to another.
    
    Moves the specified endpoint from the source pool to the target pool
    in a single atomic operation.
    """
    logger.info(f"Moving endpoint {endpoint_id} from pool {pool_id} to pool {target_pool_id}")
    
    try:
        success = await pool_manager.move_endpoint_to_pool(endpoint_id, pool_id, target_pool_id)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to move endpoint {endpoint_id} from pool {pool_id} to pool {target_pool_id}"
            )
        
        logger.info(f"Successfully moved endpoint {endpoint_id} from pool {pool_id} to pool {target_pool_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving endpoint between pools: {e}")
        raise HTTPException(status_code=500, detail="Failed to move endpoint between pools")