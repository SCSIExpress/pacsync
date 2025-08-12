"""
Package States API endpoints for the Pacman Sync Utility.

This module implements FastAPI endpoints for managing package states,
including state retrieval, submission, and historical state access.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from shared.models import SystemState, PackageState, Endpoint
from server.core.sync_coordinator import SyncCoordinator
from server.database.orm import ValidationError, NotFoundError

logger = logging.getLogger(__name__)
router = APIRouter()

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_authenticate_endpoint(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Endpoint:
    """Get the authenticate_endpoint dependency from app state."""
    auth_func = request.app.state.authenticate_endpoint
    return await auth_func(request, credentials)


# Request/Response Models
class StateSubmissionRequest(BaseModel):
    """Request model for state submission."""
    endpoint_id: str
    timestamp: str
    packages: List[Dict[str, Any]]
    pacman_version: str
    architecture: str


class StateResponse(BaseModel):
    """Response model for state information."""
    id: str
    endpoint_id: str
    pool_id: str
    timestamp: str
    packages: List[Dict[str, Any]]
    pacman_version: str
    architecture: str
    is_target: bool
    created_at: str


class StateListResponse(BaseModel):
    """Response model for state lists."""
    states: List[StateResponse]
    total_count: int


# Dependency to get sync coordinator
async def get_sync_coordinator(request: Request) -> SyncCoordinator:
    """Get sync coordinator from app state."""
    return request.app.state.sync_coordinator


def system_state_to_response(state: SystemState, state_id: str = None, pool_id: str = None) -> StateResponse:
    """Convert SystemState model to response format."""
    return StateResponse(
        id=state_id or f"state_{state.timestamp.timestamp()}",
        endpoint_id=state.endpoint_id,
        pool_id=pool_id or "",
        timestamp=state.timestamp.isoformat(),
        packages=[
            {
                "package_name": pkg.package_name,
                "version": pkg.version,
                "repository": pkg.repository,
                "installed_size": pkg.installed_size,
                "dependencies": pkg.dependencies
            }
            for pkg in state.packages
        ],
        pacman_version=state.pacman_version,
        architecture=state.architecture,
        is_target=False,  # Would need to be determined from database
        created_at=state.timestamp.isoformat()
    )


@router.post("/states/{endpoint_id}")
async def submit_state(
    endpoint_id: str,
    state_request: StateSubmissionRequest,
    request: Request,
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator),
    current_endpoint: Endpoint = Depends(get_authenticate_endpoint)
):
    """
    Submit a new package state for an endpoint.
    
    This endpoint allows clients to submit their current package state
    to be stored and potentially used as a synchronization target.
    """
    # Verify endpoint can only submit its own state
    if current_endpoint.id != endpoint_id:
        raise HTTPException(status_code=403, detail="Can only submit own endpoint state")
    
    try:
        logger.info(f"Submitting state for endpoint: {endpoint_id}")
        
        # Convert request to SystemState
        packages = []
        for pkg_data in state_request.packages:
            packages.append(PackageState(
                package_name=pkg_data['package_name'],
                version=pkg_data['version'],
                repository=pkg_data['repository'],
                installed_size=pkg_data.get('installed_size', 0),
                dependencies=pkg_data.get('dependencies', [])
            ))
        
        system_state = SystemState(
            endpoint_id=state_request.endpoint_id,
            timestamp=datetime.fromisoformat(state_request.timestamp),
            packages=packages,
            pacman_version=state_request.pacman_version,
            architecture=state_request.architecture
        )
        
        # Save the state using sync coordinator's state manager
        state_id = await sync_coordinator.state_manager.save_state(endpoint_id, system_state)
        
        logger.info(f"State submitted successfully: {state_id}")
        return {
            "message": "State submitted successfully",
            "state_id": state_id,
            "endpoint_id": endpoint_id
        }
        
    except ValidationError as e:
        logger.warning(f"Validation error in state submission: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting state for endpoint {endpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=f"State submission failed: {str(e)}")


@router.get("/states/{state_id}")
async def get_state(
    state_id: str,
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
):
    """
    Get a specific package state by ID.
    
    This endpoint retrieves detailed information about a specific
    package state, including all packages and metadata.
    """
    try:
        # Note: This would require implementing get_state_by_id in sync_coordinator
        # For now, return a not implemented error
        raise HTTPException(
            status_code=501, 
            detail="State retrieval by ID not yet implemented"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting state {state_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get state: {str(e)}")


@router.get("/states/endpoint/{endpoint_id}")
async def get_endpoint_states(
    endpoint_id: str,
    request: Request,
    limit: int = 10,
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator),
    current_endpoint: Endpoint = Depends(get_authenticate_endpoint)
):
    """
    Get historical states for an endpoint.
    
    This endpoint returns a list of historical package states
    for the specified endpoint, ordered by creation time.
    """
    # Verify endpoint can only view its own states
    if current_endpoint.id != endpoint_id:
        raise HTTPException(status_code=403, detail="Can only view own endpoint states")
    
    try:
        states = await sync_coordinator.state_manager.get_endpoint_states(endpoint_id, limit)
        
        # Convert to response format
        response_states = []
        for state in states:
            response_states.append(system_state_to_response(state, pool_id=current_endpoint.pool_id))
        
        return StateListResponse(
            states=response_states,
            total_count=len(response_states)
        )
        
    except Exception as e:
        logger.error(f"Error getting states for endpoint {endpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get endpoint states: {str(e)}")


@router.get("/states/pool/{pool_id}")
async def get_pool_states(
    pool_id: str,
    limit: int = 20,
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
):
    """
    Get recent states across all endpoints in a pool.
    
    This endpoint returns recent package states from all endpoints
    in the specified pool, useful for pool management and analysis.
    """
    try:
        # Note: This would require implementing get_pool_states in sync_coordinator
        # For now, return a not implemented error
        raise HTTPException(
            status_code=501, 
            detail="Pool state retrieval not yet implemented"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting states for pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pool states: {str(e)}")


# Health check endpoint for states service
@router.get("/states/health")
async def states_health_check():
    """Health check endpoint for states service."""
    return {
        "status": "healthy",
        "service": "package-states",
        "timestamp": datetime.now().isoformat()
    }