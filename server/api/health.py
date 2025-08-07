"""
Health check endpoints for container orchestration and monitoring.

This module provides comprehensive health check endpoints that can be used
by container orchestrators, load balancers, and monitoring systems.
"""

import logging
import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from server.database.connection import DatabaseManager
from server.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter()

# Global health status tracking
_health_status = {
    "startup_time": time.time(),
    "last_database_check": None,
    "database_status": "unknown",
    "service_status": "starting"
}


async def get_database_manager() -> DatabaseManager:
    """Dependency to get database manager from app state."""
    from server.api.main import app
    return app.state.db_manager


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


async def check_database_health(db_manager: DatabaseManager) -> Dict[str, Any]:
    """Check database connectivity and performance."""
    try:
        start_time = time.time()
        
        # Test basic connectivity
        await db_manager.execute("SELECT 1")
        
        # Test more complex query for performance
        if db_manager.database_type == "postgresql":
            await db_manager.fetchval("SELECT COUNT(*) FROM information_schema.tables")
        else:  # SQLite
            await db_manager.fetchval("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Update global status
        _health_status["last_database_check"] = time.time()
        _health_status["database_status"] = "healthy"
        
        return {
            "status": "healthy",
            "type": db_manager.database_type,
            "response_time_ms": round(response_time, 2),
            "last_check": get_current_timestamp()
        }
    except Exception as e:
        _health_status["database_status"] = "unhealthy"
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "type": db_manager.database_type,
            "error": str(e),
            "last_check": get_current_timestamp()
        }


async def check_service_dependencies() -> Dict[str, Any]:
    """Check health of service dependencies and core components."""
    dependencies = {}
    
    try:
        from server.api.main import app
        
        # Check if core services are initialized
        if hasattr(app.state, 'pool_manager'):
            dependencies["pool_manager"] = "healthy"
        else:
            dependencies["pool_manager"] = "not_initialized"
        
        if hasattr(app.state, 'sync_coordinator'):
            dependencies["sync_coordinator"] = "healthy"
        else:
            dependencies["sync_coordinator"] = "not_initialized"
        
        if hasattr(app.state, 'endpoint_manager'):
            dependencies["endpoint_manager"] = "healthy"
        else:
            dependencies["endpoint_manager"] = "not_initialized"
        
        return dependencies
    except Exception as e:
        logger.error(f"Service dependency check failed: {e}")
        return {"error": str(e)}


@router.get("/health")
async def basic_health_check():
    """
    Basic health check endpoint for simple liveness probes.
    
    Returns 200 OK if the service is running, 503 if there are critical issues.
    """
    try:
        uptime = time.time() - _health_status["startup_time"]
        
        # Check if database was recently verified
        db_check_age = None
        if _health_status["last_database_check"]:
            db_check_age = time.time() - _health_status["last_database_check"]
        
        # Consider service unhealthy if database hasn't been checked in 5 minutes
        if db_check_age is None or db_check_age > 300:
            status_code = 503
            status = "unhealthy"
        elif _health_status["database_status"] == "unhealthy":
            status_code = 503
            status = "unhealthy"
        else:
            status_code = 200
            status = "healthy"
        
        response = {
            "status": status,
            "service": "pacman-sync-utility",
            "version": "1.0.0",
            "uptime_seconds": round(uptime, 2),
            "timestamp": get_current_timestamp()
        }
        
        return JSONResponse(content=response, status_code=status_code)
    
    except Exception as e:
        logger.error(f"Basic health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": get_current_timestamp()
            },
            status_code=503
        )


@router.get("/health/detailed")
async def detailed_health_check(db_manager: DatabaseManager = Depends(get_database_manager)):
    """
    Detailed health check endpoint for comprehensive monitoring.
    
    Provides detailed information about all service components and dependencies.
    """
    try:
        config = get_config()
        uptime = time.time() - _health_status["startup_time"]
        
        # Check database health
        database_health = await check_database_health(db_manager)
        
        # Check service dependencies
        dependencies = await check_service_dependencies()
        
        # Determine overall health status
        overall_status = "healthy"
        if database_health["status"] != "healthy":
            overall_status = "unhealthy"
        elif any(dep != "healthy" for dep in dependencies.values() if isinstance(dep, str)):
            overall_status = "degraded"
        
        response = {
            "status": overall_status,
            "service": "pacman-sync-utility",
            "version": "1.0.0",
            "timestamp": get_current_timestamp(),
            "uptime_seconds": round(uptime, 2),
            "environment": config.server.environment,
            "components": {
                "database": database_health,
                "dependencies": dependencies
            },
            "configuration": {
                "database_type": config.database.type,
                "pool_size": f"{config.database.pool_min_size}-{config.database.pool_max_size}",
                "cors_enabled": len(config.server.cors_origins) > 0,
                "features": {
                    "repository_analysis": config.features.enable_repository_analysis,
                    "auto_cleanup": config.features.auto_cleanup_old_states
                }
            }
        }
        
        status_code = 200 if overall_status == "healthy" else 503
        return JSONResponse(content=response, status_code=status_code)
    
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": get_current_timestamp()
            },
            status_code=503
        )


@router.get("/health/ready")
async def readiness_check(db_manager: DatabaseManager = Depends(get_database_manager)):
    """
    Readiness check endpoint for container orchestration.
    
    Returns 200 when the service is ready to accept traffic,
    503 when it's still starting up or has critical issues.
    """
    try:
        # Check if service has been running for at least 10 seconds
        uptime = time.time() - _health_status["startup_time"]
        if uptime < 10:
            return JSONResponse(
                content={
                    "status": "not_ready",
                    "reason": "service_starting",
                    "uptime_seconds": round(uptime, 2),
                    "timestamp": get_current_timestamp()
                },
                status_code=503
            )
        
        # Check database connectivity
        database_health = await check_database_health(db_manager)
        if database_health["status"] != "healthy":
            return JSONResponse(
                content={
                    "status": "not_ready",
                    "reason": "database_unhealthy",
                    "database": database_health,
                    "timestamp": get_current_timestamp()
                },
                status_code=503
            )
        
        # Check core services
        dependencies = await check_service_dependencies()
        if any(dep != "healthy" for dep in dependencies.values() if isinstance(dep, str)):
            return JSONResponse(
                content={
                    "status": "not_ready",
                    "reason": "dependencies_not_ready",
                    "dependencies": dependencies,
                    "timestamp": get_current_timestamp()
                },
                status_code=503
            )
        
        return JSONResponse(
            content={
                "status": "ready",
                "uptime_seconds": round(uptime, 2),
                "timestamp": get_current_timestamp()
            },
            status_code=200
        )
    
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            content={
                "status": "not_ready",
                "reason": "check_failed",
                "error": str(e),
                "timestamp": get_current_timestamp()
            },
            status_code=503
        )


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check endpoint for container orchestration.
    
    Returns 200 if the service process is alive and responsive,
    regardless of the health of dependencies.
    """
    try:
        uptime = time.time() - _health_status["startup_time"]
        
        return JSONResponse(
            content={
                "status": "alive",
                "uptime_seconds": round(uptime, 2),
                "timestamp": get_current_timestamp()
            },
            status_code=200
        )
    
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "error": str(e),
                "timestamp": get_current_timestamp()
            },
            status_code=503
        )


def update_service_status(status: str):
    """Update the global service status."""
    _health_status["service_status"] = status
    logger.info(f"Service status updated to: {status}")


def mark_service_ready():
    """Mark the service as ready to accept traffic."""
    update_service_status("ready")


def mark_service_shutting_down():
    """Mark the service as shutting down."""
    update_service_status("shutting_down")