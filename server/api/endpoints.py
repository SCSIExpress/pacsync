"""
Endpoint Management API endpoints for the Pacman Sync Utility.

This module implements FastAPI endpoints for endpoint registration,
status updates, removal, and repository information management.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator

from shared.models import Endpoint, Repository, RepositoryPackage, SyncStatus
from server.core.endpoint_manager import EndpointManager, EndpointAuthenticationError
from server.middleware.validation import (
    validate_endpoint_name, validate_hostname, validate_package_name,
    validate_version, validate_repository_name, validate_url
)

logger = logging.getLogger(__name__)
router = APIRouter()

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


# Request/Response Models
class EndpointRegistrationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Endpoint name")
    hostname: str = Field(..., min_length=1, max_length=255, description="Endpoint hostname")
    
    @validator('name')
    def validate_name(cls, v):
        return validate_endpoint_name(v)
    
    @validator('hostname')
    def validate_hostname_field(cls, v):
        return validate_hostname(v)


class EndpointRegistrationResponse(BaseModel):
    endpoint: Dict[str, Any]
    auth_token: str


class EndpointStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Sync status (in_sync, ahead, behind, offline)")


class RepositoryPackageData(BaseModel):
    name: str
    version: str
    repository: str
    architecture: str
    description: Optional[str] = None
    
    @validator('name')
    def validate_package_name_field(cls, v):
        return validate_package_name(v)
    
    @validator('version')
    def validate_version_field(cls, v):
        return validate_version(v)
    
    @validator('repository')
    def validate_repository_field(cls, v):
        return validate_repository_name(v)


class RepositoryData(BaseModel):
    repo_name: str
    repo_url: Optional[str] = None
    packages: List[RepositoryPackageData]
    
    @validator('repo_name')
    def validate_repo_name(cls, v):
        return validate_repository_name(v)
    
    @validator('repo_url')
    def validate_repo_url(cls, v):
        if v is not None:
            return validate_url(v)
        return v


class RepositorySubmissionRequest(BaseModel):
    repositories: List[RepositoryData]


class EndpointResponse(BaseModel):
    id: str
    name: str
    hostname: str
    pool_id: Optional[str]
    last_seen: Optional[str]
    sync_status: str
    created_at: str
    updated_at: str


# Dependency to get endpoint manager
async def get_endpoint_manager(request: Request) -> EndpointManager:
    """Get endpoint manager from app state."""
    if not hasattr(request.app.state, 'endpoint_manager'):
        # Initialize endpoint manager if not exists
        db_manager = request.app.state.db_manager
        request.app.state.endpoint_manager = EndpointManager(db_manager)
    return request.app.state.endpoint_manager


# Get authentication dependency from app state
async def get_authenticate_endpoint(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Endpoint:
    """Get endpoint authentication dependency from app state."""
    auth_func = request.app.state.authenticate_endpoint
    return await auth_func(request, credentials)


def endpoint_to_response(endpoint: Endpoint) -> EndpointResponse:
    """Convert Endpoint model to response format."""
    return EndpointResponse(
        id=endpoint.id,
        name=endpoint.name,
        hostname=endpoint.hostname,
        pool_id=endpoint.pool_id,
        last_seen=endpoint.last_seen.isoformat() if endpoint.last_seen else None,
        sync_status=endpoint.sync_status.value,
        created_at=endpoint.created_at.isoformat(),
        updated_at=endpoint.updated_at.isoformat()
    )


@router.post("/endpoints/register", response_model=EndpointRegistrationResponse)
async def register_endpoint(
    request: EndpointRegistrationRequest,
    endpoint_manager: EndpointManager = Depends(get_endpoint_manager)
):
    """Register a new endpoint."""
    try:
        logger.info(f"Registering endpoint: {request.name}@{request.hostname}")
        
        # Register endpoint
        endpoint = await endpoint_manager.register_endpoint(request.name, request.hostname)
        
        # Generate authentication token
        auth_token = endpoint_manager.generate_auth_token(endpoint.id, endpoint.name)
        
        return EndpointRegistrationResponse(
            endpoint={
                "id": endpoint.id,
                "name": endpoint.name,
                "hostname": endpoint.hostname,
                "pool_id": endpoint.pool_id,
                "sync_status": endpoint.sync_status.value,
                "created_at": endpoint.created_at.isoformat(),
                "updated_at": endpoint.updated_at.isoformat()
            },
            auth_token=auth_token
        )
        
    except Exception as e:
        logger.error(f"Failed to register endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.get("/endpoints", response_model=List[EndpointResponse])
async def list_endpoints(
    pool_id: Optional[str] = None,
    endpoint_manager: EndpointManager = Depends(get_endpoint_manager)
):
    """List all endpoints, optionally filtered by pool."""
    try:
        endpoints = await endpoint_manager.list_endpoints(pool_id)
        return [endpoint_to_response(endpoint) for endpoint in endpoints]
        
    except Exception as e:
        logger.error(f"Failed to list endpoints: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list endpoints: {str(e)}")


@router.get("/endpoints/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint(
    endpoint_id: str,
    endpoint_manager: EndpointManager = Depends(get_endpoint_manager)
):
    """Get endpoint details by ID."""
    try:
        endpoint = await endpoint_manager.get_endpoint(endpoint_id)
        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        return endpoint_to_response(endpoint)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get endpoint {endpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get endpoint: {str(e)}")


@router.put("/endpoints/{endpoint_id}/status")
async def update_endpoint_status(
    endpoint_id: str,
    status_request: EndpointStatusUpdateRequest,
    request: Request,
    endpoint_manager: EndpointManager = Depends(get_endpoint_manager),
    current_endpoint: Endpoint = Depends(get_authenticate_endpoint)
):
    """Update endpoint sync status."""
    
    # Verify endpoint can only update its own status
    if current_endpoint.id != endpoint_id:
        raise HTTPException(status_code=403, detail="Can only update own endpoint status")
    
    try:
        # Validate status
        try:
            status = SyncStatus(status_request.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_request.status}")
        
        success = await endpoint_manager.update_endpoint_status(endpoint_id, status)
        if not success:
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        return {"message": "Status updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update endpoint status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")


@router.delete("/endpoints/{endpoint_id}")
async def remove_endpoint(
    endpoint_id: str,
    request: Request,
    endpoint_manager: EndpointManager = Depends(get_endpoint_manager),
    current_endpoint: Endpoint = Depends(get_authenticate_endpoint)
):
    """Remove an endpoint."""
    
    # Verify endpoint can only remove itself
    if current_endpoint.id != endpoint_id:
        raise HTTPException(status_code=403, detail="Can only remove own endpoint")
    
    try:
        success = await endpoint_manager.remove_endpoint(endpoint_id)
        if not success:
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        return {"message": "Endpoint removed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove endpoint: {str(e)}")


@router.post("/endpoints/{endpoint_id}/repositories")
async def submit_repository_info(
    endpoint_id: str,
    repo_request: RepositorySubmissionRequest,
    request: Request,
    endpoint_manager: EndpointManager = Depends(get_endpoint_manager),
    current_endpoint: Endpoint = Depends(get_authenticate_endpoint)
):
    """Submit repository information for an endpoint."""
    
    # Verify endpoint can only submit its own repository info
    if current_endpoint.id != endpoint_id:
        raise HTTPException(status_code=403, detail="Can only submit own repository information")
    
    try:
        # Convert request data to Repository objects
        repositories = []
        for repo_data in repo_request.repositories:
            packages = []
            for pkg_data in repo_data.packages:
                packages.append(RepositoryPackage(
                    name=pkg_data.name,
                    version=pkg_data.version,
                    repository=pkg_data.repository,
                    architecture=pkg_data.architecture,
                    description=pkg_data.description
                ))
            
            repositories.append(Repository(
                id="",  # Will be generated
                endpoint_id=endpoint_id,
                repo_name=repo_data.repo_name,
                repo_url=repo_data.repo_url,
                packages=packages
            ))
        
        success = await endpoint_manager.update_repository_info(endpoint_id, repositories)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update repository information")
        
        return {"message": "Repository information updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit repository info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit repository info: {str(e)}")


@router.get("/endpoints/{endpoint_id}/repositories")
async def get_repository_info(
    endpoint_id: str,
    endpoint_manager: EndpointManager = Depends(get_endpoint_manager)
):
    """Get repository information for an endpoint."""
    try:
        # Verify endpoint exists
        endpoint = await endpoint_manager.get_endpoint(endpoint_id)
        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        repositories = await endpoint_manager.get_repository_info(endpoint_id)
        
        # Convert to response format
        response_data = []
        for repo in repositories:
            packages_data = []
            for pkg in repo.packages:
                packages_data.append({
                    "name": pkg.name,
                    "version": pkg.version,
                    "repository": pkg.repository,
                    "architecture": pkg.architecture,
                    "description": pkg.description
                })
            
            response_data.append({
                "id": repo.id,
                "repo_name": repo.repo_name,
                "repo_url": repo.repo_url,
                "packages": packages_data,
                "last_updated": repo.last_updated.isoformat()
            })
        
        return {"repositories": response_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get repository info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get repository info: {str(e)}")


@router.put("/endpoints/{endpoint_id}/pool")
async def assign_endpoint_to_pool(
    endpoint_id: str,
    pool_id: str,
    endpoint_manager: EndpointManager = Depends(get_endpoint_manager)
):
    """Assign endpoint to a pool. (Admin operation)"""
    try:
        success = await endpoint_manager.assign_to_pool(endpoint_id, pool_id)
        if not success:
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        return {"message": "Endpoint assigned to pool successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign endpoint to pool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assign endpoint: {str(e)}")


@router.delete("/endpoints/{endpoint_id}/pool")
async def remove_endpoint_from_pool(
    endpoint_id: str,
    endpoint_manager: EndpointManager = Depends(get_endpoint_manager)
):
    """Remove endpoint from its pool. (Admin operation)"""
    try:
        success = await endpoint_manager.remove_from_pool(endpoint_id)
        if not success:
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        return {"message": "Endpoint removed from pool successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove endpoint from pool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove endpoint from pool: {str(e)}")