"""
Package Sync API endpoints for Pacman Sync Utility.

This module provides endpoints for managing package sync states, counting packages
in target states, and providing endpoints the ability to sync to target packages.
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel

from server.core.sync_coordinator import SyncCoordinator
from server.core.pool_manager import PackagePoolManager
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from shared.models import Endpoint, PackageState, SyncStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/package-sync", tags=["package-sync"])


class PackageCountResponse(BaseModel):
    """Response for package count queries."""
    pool_id: str
    target_state_id: Optional[str]
    total_packages: int
    packages_by_repository: Dict[str, int]
    architecture: Optional[str]
    last_updated: Optional[str]


class PackageSyncStatusResponse(BaseModel):
    """Response for package sync status."""
    endpoint_id: str
    pool_id: Optional[str]
    sync_status: str
    target_packages: int
    current_packages: int
    packages_to_install: int
    packages_to_upgrade: int
    packages_to_remove: int
    last_sync: Optional[str]


class PackageSyncRequest(BaseModel):
    """Request to sync packages to target state."""
    dry_run: bool = False
    force: bool = False


# Security
security = HTTPBearer()

# Dependencies
async def get_sync_coordinator(request: Request) -> SyncCoordinator:
    """Get sync coordinator from app state."""
    return request.app.state.sync_coordinator


async def get_pool_manager(request: Request) -> PackagePoolManager:
    """Get pool manager from app state."""
    return request.app.state.pool_manager


async def get_authenticate_endpoint(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Endpoint:
    """Get endpoint authentication dependency from app state."""
    auth_func = request.app.state.authenticate_endpoint
    return await auth_func(request, credentials)


@router.get("/pools/{pool_id}/package-count")
async def get_pool_package_count(
    pool_id: str,
    pool_manager: PackagePoolManager = Depends(get_pool_manager),
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
) -> PackageCountResponse:
    """
    Get the count of packages in the pool's target sync state.
    
    This endpoint returns information about the packages that are currently
    set as the sync target for the pool, which all endpoints should sync to.
    """
    try:
        logger.info(f"Getting package count for pool: {pool_id}")
        
        # Get pool information
        pool = await pool_manager.get_pool(pool_id)
        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")
        
        # Get target state
        target_state_id = pool.target_state_id
        if not target_state_id:
            return PackageCountResponse(
                pool_id=pool_id,
                target_state_id=None,
                total_packages=0,
                packages_by_repository={},
                architecture=None,
                last_updated=None
            )
        
        # Get target state details
        target_state = await sync_coordinator.state_manager.get_state(target_state_id)
        if not target_state:
            raise HTTPException(status_code=404, detail="Target state not found")
        
        # Count packages by repository
        packages_by_repo = {}
        for package in target_state.packages:
            repo = package.repository
            packages_by_repo[repo] = packages_by_repo.get(repo, 0) + 1
        
        return PackageCountResponse(
            pool_id=pool_id,
            target_state_id=target_state_id,
            total_packages=len(target_state.packages),
            packages_by_repository=packages_by_repo,
            architecture=target_state.architecture,
            last_updated=target_state.timestamp.isoformat() if target_state.timestamp else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get package count for pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get package count: {str(e)}")


@router.get("/endpoints/{endpoint_id}/sync-status")
async def get_endpoint_sync_status(
    endpoint_id: str,
    pool_manager: PackagePoolManager = Depends(get_pool_manager),
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator),
    current_endpoint: Endpoint = Depends(get_authenticate_endpoint)
) -> PackageSyncStatusResponse:
    """
    Get the package sync status for an endpoint.
    
    This shows how many packages the endpoint needs to sync to match
    the pool's target state.
    """
    try:
        # Verify endpoint can only check its own status
        if current_endpoint.id != endpoint_id:
            raise HTTPException(status_code=403, detail="Can only check own sync status")
        
        logger.info(f"Getting sync status for endpoint: {endpoint_id}")
        
        # Get endpoint information
        endpoint = await pool_manager.endpoint_repo.get_by_id(endpoint_id)
        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        # If not in a pool, return basic status
        if not endpoint.pool_id:
            return PackageSyncStatusResponse(
                endpoint_id=endpoint_id,
                pool_id=None,
                sync_status=endpoint.sync_status.value,
                target_packages=0,
                current_packages=0,
                packages_to_install=0,
                packages_to_upgrade=0,
                packages_to_remove=0,
                last_sync=None
            )
        
        # Get pool and target state
        pool = await pool_manager.get_pool(endpoint.pool_id)
        if not pool or not pool.target_state_id:
            return PackageSyncStatusResponse(
                endpoint_id=endpoint_id,
                pool_id=endpoint.pool_id,
                sync_status=endpoint.sync_status.value,
                target_packages=0,
                current_packages=0,
                packages_to_install=0,
                packages_to_upgrade=0,
                packages_to_remove=0,
                last_sync=None
            )
        
        # Get target state
        target_state = await sync_coordinator.state_manager.get_state(pool.target_state_id)
        if not target_state:
            raise HTTPException(status_code=404, detail="Target state not found")
        
        # Get current endpoint state
        endpoint_states = await sync_coordinator.state_manager.get_endpoint_states(endpoint_id, 1)
        current_state = endpoint_states[0] if endpoint_states else None
        
        # Calculate sync differences
        target_packages = len(target_state.packages)
        current_packages = len(current_state.packages) if current_state else 0
        
        packages_to_install = 0
        packages_to_upgrade = 0
        packages_to_remove = 0
        
        if current_state:
            # Create package maps for comparison
            target_pkg_map = {pkg.package_name: pkg for pkg in target_state.packages}
            current_pkg_map = {pkg.package_name: pkg for pkg in current_state.packages}
            
            # Count differences
            for pkg_name, target_pkg in target_pkg_map.items():
                if pkg_name not in current_pkg_map:
                    packages_to_install += 1
                elif current_pkg_map[pkg_name].version != target_pkg.version:
                    packages_to_upgrade += 1
            
            for pkg_name in current_pkg_map:
                if pkg_name not in target_pkg_map:
                    packages_to_remove += 1
        else:
            # No current state, all target packages need to be installed
            packages_to_install = target_packages
        
        return PackageSyncStatusResponse(
            endpoint_id=endpoint_id,
            pool_id=endpoint.pool_id,
            sync_status=endpoint.sync_status.value,
            target_packages=target_packages,
            current_packages=current_packages,
            packages_to_install=packages_to_install,
            packages_to_upgrade=packages_to_upgrade,
            packages_to_remove=packages_to_remove,
            last_sync=current_state.timestamp.isoformat() if current_state and current_state.timestamp else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync status for endpoint {endpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")


@router.post("/endpoints/{endpoint_id}/sync")
async def sync_endpoint_packages(
    endpoint_id: str,
    sync_request: PackageSyncRequest,
    pool_manager: PackagePoolManager = Depends(get_pool_manager),
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator),
    current_endpoint: Endpoint = Depends(get_authenticate_endpoint)
):
    """
    Sync endpoint packages to the pool's target state.
    
    This endpoint allows an endpoint to sync its packages to match
    the pool's target package state.
    """
    try:
        # Verify endpoint can only sync itself
        if current_endpoint.id != endpoint_id:
            raise HTTPException(status_code=403, detail="Can only sync own packages")
        
        logger.info(f"Starting package sync for endpoint: {endpoint_id} (dry_run: {sync_request.dry_run})")
        
        # Get endpoint information
        endpoint = await pool_manager.endpoint_repo.get_by_id(endpoint_id)
        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        if not endpoint.pool_id:
            raise HTTPException(status_code=400, detail="Endpoint is not assigned to a pool")
        
        # Get pool and target state
        pool = await pool_manager.get_pool(endpoint.pool_id)
        if not pool or not pool.target_state_id:
            raise HTTPException(status_code=400, detail="Pool has no target state set")
        
        # Trigger sync operation
        if sync_request.dry_run:
            # For dry run, just return what would be done
            sync_status = await get_endpoint_sync_status(
                endpoint_id, pool_manager, sync_coordinator, current_endpoint
            )
            
            return {
                "message": "Dry run completed",
                "dry_run": True,
                "changes": {
                    "packages_to_install": sync_status.packages_to_install,
                    "packages_to_upgrade": sync_status.packages_to_upgrade,
                    "packages_to_remove": sync_status.packages_to_remove
                }
            }
        else:
            # Perform actual sync
            sync_operation = await sync_coordinator.sync_to_latest(endpoint_id)
            
            return {
                "message": "Sync operation started",
                "operation_id": sync_operation.id,
                "status": sync_operation.status.value,
                "dry_run": False
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync packages for endpoint {endpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync packages: {str(e)}")


@router.get("/pools/{pool_id}/endpoints/sync-summary")
async def get_pool_sync_summary(
    pool_id: str,
    pool_manager: PackagePoolManager = Depends(get_pool_manager),
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
):
    """
    Get a summary of sync status for all endpoints in a pool.
    
    This provides an overview of how many endpoints are in sync,
    behind, or have other sync statuses.
    """
    try:
        logger.info(f"Getting sync summary for pool: {pool_id}")
        
        # Get pool information
        pool = await pool_manager.get_pool(pool_id)
        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")
        
        # Get all endpoints in the pool
        endpoints = await pool_manager.endpoint_repo.list_by_pool(pool_id)
        
        # Count by sync status
        status_counts = {}
        total_endpoints = len(endpoints)
        
        for endpoint in endpoints:
            status = endpoint.sync_status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Get target package count
        target_packages = 0
        if pool.target_state_id:
            target_state = await sync_coordinator.state_manager.get_state(pool.target_state_id)
            if target_state:
                target_packages = len(target_state.packages)
        
        return {
            "pool_id": pool_id,
            "total_endpoints": total_endpoints,
            "target_packages": target_packages,
            "sync_status_counts": status_counts,
            "endpoints": [
                {
                    "id": endpoint.id,
                    "name": endpoint.name,
                    "hostname": endpoint.hostname,
                    "sync_status": endpoint.sync_status.value,
                    "last_seen": endpoint.last_seen.isoformat() if endpoint.last_seen else None
                }
                for endpoint in endpoints
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync summary for pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sync summary: {str(e)}")


# Health check endpoint
@router.get("/health")
async def package_sync_health_check():
    """Health check endpoint for package sync service."""
    return {
        "status": "healthy",
        "service": "package-sync",
        "timestamp": "2025-08-13T12:40:00Z"
    }