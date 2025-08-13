"""
Dashboard API endpoints for Pacman Sync Utility.

This module provides endpoints for dashboard metrics including server uptime,
endpoint counts, repository counts, package counts, and system statistics.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from server.core.pool_manager import PackagePoolManager
from server.core.sync_coordinator import SyncCoordinator
from server.database.orm import EndpointRepository, RepositoryRepository, PackageStateRepository
from server.database.connection import get_database_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Store server start time
SERVER_START_TIME = datetime.now()


class DashboardMetrics(BaseModel):
    """Dashboard metrics response model."""
    server_uptime_seconds: int
    server_uptime_human: str
    total_endpoints: int
    endpoints_online: int
    endpoints_offline: int
    endpoints_unassigned: int
    total_pools: int
    pools_healthy: int
    pools_with_issues: int
    total_repositories: int
    total_packages_available: int
    total_packages_in_target_states: int
    average_sync_percentage: float
    last_updated: str


class SystemStats(BaseModel):
    """System statistics response model."""
    database_type: str
    total_sync_operations: int
    successful_syncs_24h: int
    failed_syncs_24h: int
    most_active_pool: str
    most_active_endpoint: str


# Dependencies
async def get_pool_manager(request: Request) -> PackagePoolManager:
    """Get pool manager from app state."""
    return request.app.state.pool_manager


async def get_sync_coordinator(request: Request) -> SyncCoordinator:
    """Get sync coordinator from app state."""
    return request.app.state.sync_coordinator


@router.get("/metrics")
async def get_dashboard_metrics(
    pool_manager: PackagePoolManager = Depends(get_pool_manager),
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
) -> DashboardMetrics:
    """
    Get comprehensive dashboard metrics.
    
    Returns server uptime, endpoint counts, pool statistics, repository counts,
    package counts, and sync status information.
    """
    try:
        logger.info("Getting dashboard metrics")
        
        # Calculate server uptime
        uptime_delta = datetime.now() - SERVER_START_TIME
        uptime_seconds = int(uptime_delta.total_seconds())
        uptime_human = format_uptime(uptime_delta)
        
        # Get all pools and their statuses
        pools = await pool_manager.list_pools()
        total_pools = len(pools)
        
        # Get pool status information
        pool_statuses = []
        pools_healthy = 0
        total_sync_percentage = 0.0
        
        for pool in pools:
            try:
                endpoints = await pool_manager.endpoint_repo.list_by_pool(pool.id)
                
                # Calculate sync stats for this pool
                in_sync_count = len([e for e in endpoints if e.sync_status.value == 'in_sync'])
                total_endpoints_in_pool = len(endpoints)
                
                if total_endpoints_in_pool > 0:
                    sync_percentage = (in_sync_count / total_endpoints_in_pool) * 100.0
                else:
                    sync_percentage = 100.0
                
                total_sync_percentage += sync_percentage
                
                # Consider pool healthy if >80% in sync or empty
                if sync_percentage >= 80.0 or total_endpoints_in_pool == 0:
                    pools_healthy += 1
                
                pool_statuses.append({
                    'pool': pool,
                    'endpoints': endpoints,
                    'sync_percentage': sync_percentage
                })
                
            except Exception as e:
                logger.warning(f"Error getting status for pool {pool.id}: {e}")
                # Count as unhealthy pool
                pool_statuses.append({
                    'pool': pool,
                    'endpoints': [],
                    'sync_percentage': 0.0
                })
        
        # Calculate average sync percentage
        average_sync_percentage = total_sync_percentage / total_pools if total_pools > 0 else 0.0
        
        # Get all endpoints
        all_endpoints = await pool_manager.endpoint_repo.list_by_pool(None)
        total_endpoints = len(all_endpoints)
        
        # Count endpoint statuses
        endpoints_online = len([e for e in all_endpoints if e.sync_status.value in ['in_sync', 'ahead', 'behind']])
        endpoints_offline = len([e for e in all_endpoints if e.sync_status.value == 'offline'])
        endpoints_unassigned = len([e for e in all_endpoints if e.pool_id is None])
        
        # Get repository statistics
        total_repositories = await get_total_repositories()
        total_packages_available = await get_total_packages_available()
        total_packages_in_target_states = await get_total_packages_in_target_states()
        
        return DashboardMetrics(
            server_uptime_seconds=uptime_seconds,
            server_uptime_human=uptime_human,
            total_endpoints=total_endpoints,
            endpoints_online=endpoints_online,
            endpoints_offline=endpoints_offline,
            endpoints_unassigned=endpoints_unassigned,
            total_pools=total_pools,
            pools_healthy=pools_healthy,
            pools_with_issues=total_pools - pools_healthy,
            total_repositories=total_repositories,
            total_packages_available=total_packages_available,
            total_packages_in_target_states=total_packages_in_target_states,
            average_sync_percentage=round(average_sync_percentage, 1),
            last_updated=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to get dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard metrics: {str(e)}")


@router.get("/pool-statuses")
async def get_pool_statuses(
    pool_manager: PackagePoolManager = Depends(get_pool_manager)
) -> List[Dict[str, Any]]:
    """
    Get status information for all pools.
    
    This is a working replacement for the problematic /pools/status endpoint.
    """
    try:
        logger.info("Getting pool statuses for dashboard")
        
        pools = await pool_manager.list_pools()
        statuses = []
        
        for pool in pools:
            try:
                endpoints = await pool_manager.endpoint_repo.list_by_pool(pool.id)
                
                # Calculate status counts
                in_sync_count = len([e for e in endpoints if e.sync_status.value == 'in_sync'])
                ahead_count = len([e for e in endpoints if e.sync_status.value == 'ahead'])
                behind_count = len([e for e in endpoints if e.sync_status.value == 'behind'])
                offline_count = len([e for e in endpoints if e.sync_status.value == 'offline'])
                total_endpoints = len(endpoints)
                
                # Calculate sync percentage
                if total_endpoints > 0:
                    sync_percentage = (in_sync_count / total_endpoints) * 100.0
                else:
                    sync_percentage = 100.0
                
                # Determine overall status
                if total_endpoints == 0:
                    overall_status = "empty"
                elif in_sync_count == total_endpoints:
                    overall_status = "healthy"
                elif offline_count == total_endpoints:
                    overall_status = "critical"
                elif sync_percentage >= 80:
                    overall_status = "healthy"
                elif sync_percentage >= 50:
                    overall_status = "warning"
                else:
                    overall_status = "critical"
                
                statuses.append({
                    "pool_id": pool.id,
                    "pool_name": pool.name,
                    "total_endpoints": total_endpoints,
                    "in_sync_count": in_sync_count,
                    "ahead_count": ahead_count,
                    "behind_count": behind_count,
                    "offline_count": offline_count,
                    "sync_percentage": round(sync_percentage, 1),
                    "overall_status": overall_status,
                    "has_target_state": pool.target_state_id is not None,
                    "auto_sync_enabled": pool.sync_policy.auto_sync if pool.sync_policy else False
                })
                
            except Exception as e:
                logger.warning(f"Error getting status for pool {pool.id}: {e}")
                # Add pool with error status
                statuses.append({
                    "pool_id": pool.id,
                    "pool_name": pool.name,
                    "total_endpoints": 0,
                    "in_sync_count": 0,
                    "ahead_count": 0,
                    "behind_count": 0,
                    "offline_count": 0,
                    "sync_percentage": 0.0,
                    "overall_status": "error",
                    "has_target_state": False,
                    "auto_sync_enabled": False
                })
        
        return statuses
        
    except Exception as e:
        logger.error(f"Failed to get pool statuses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pool statuses: {str(e)}")


@router.get("/system-stats")
async def get_system_stats(
    pool_manager: PackagePoolManager = Depends(get_pool_manager),
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
) -> SystemStats:
    """
    Get system statistics for dashboard.
    
    Returns database information, sync operation counts, and activity statistics.
    """
    try:
        logger.info("Getting system statistics")
        
        # Get database type
        db_manager = get_database_manager()
        database_type = db_manager.database_type
        
        # Get sync operation statistics (simplified for now)
        total_sync_operations = await get_total_sync_operations()
        successful_syncs_24h = 0  # TODO: Implement when we have operation history
        failed_syncs_24h = 0     # TODO: Implement when we have operation history
        
        # Get most active pool and endpoint (simplified)
        pools = await pool_manager.list_pools()
        most_active_pool = pools[0].name if pools else "None"
        
        all_endpoints = await pool_manager.endpoint_repo.list_by_pool(None)
        most_active_endpoint = all_endpoints[0].name if all_endpoints else "None"
        
        return SystemStats(
            database_type=database_type,
            total_sync_operations=total_sync_operations,
            successful_syncs_24h=successful_syncs_24h,
            failed_syncs_24h=failed_syncs_24h,
            most_active_pool=most_active_pool,
            most_active_endpoint=most_active_endpoint
        )
        
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {str(e)}")


# Helper functions
def format_uptime(uptime_delta: timedelta) -> str:
    """Format uptime delta into human readable string."""
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


async def get_total_repositories() -> int:
    """Get total number of repositories across all endpoints."""
    try:
        db_manager = get_database_manager()
        query = "SELECT COUNT(DISTINCT repo_name) FROM repositories"
        result = await db_manager.fetchval(query)
        return result if result else 0
    except Exception as e:
        logger.warning(f"Failed to get repository count: {e}")
        return 0


async def get_total_packages_available() -> int:
    """Get total number of packages available across all repositories."""
    try:
        db_manager = get_database_manager()
        # Count packages in repositories (JSON array length)
        query = """
        SELECT SUM(
            CASE 
                WHEN packages IS NOT NULL AND packages != '[]' 
                THEN json_array_length(packages)
                ELSE 0 
            END
        ) FROM repositories
        """
        result = await db_manager.fetchval(query)
        return result if result else 0
    except Exception as e:
        logger.warning(f"Failed to get package count: {e}")
        return 0


async def get_total_packages_in_target_states() -> int:
    """Get total number of packages in target states across all pools."""
    try:
        db_manager = get_database_manager()
        # Count packages in target states
        query = """
        SELECT SUM(
            CASE 
                WHEN state_data IS NOT NULL 
                THEN json_array_length(json_extract(state_data, '$.packages'))
                ELSE 0 
            END
        ) FROM package_states WHERE is_target = 1
        """
        result = await db_manager.fetchval(query)
        return result if result else 0
    except Exception as e:
        logger.warning(f"Failed to get target state package count: {e}")
        return 0


async def get_total_sync_operations() -> int:
    """Get total number of sync operations."""
    try:
        db_manager = get_database_manager()
        query = "SELECT COUNT(*) FROM sync_operations"
        result = await db_manager.fetchval(query)
        return result if result else 0
    except Exception as e:
        logger.warning(f"Failed to get sync operation count: {e}")
        return 0


# Health check endpoint
@router.get("/health")
async def dashboard_health_check():
    """Health check endpoint for dashboard service."""
    return {
        "status": "healthy",
        "service": "dashboard",
        "timestamp": datetime.now().isoformat(),
        "uptime": format_uptime(datetime.now() - SERVER_START_TIME)
    }