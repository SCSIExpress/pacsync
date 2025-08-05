"""
Synchronization Operation API endpoints for the Pacman Sync Utility.

This module implements FastAPI endpoints for sync, set-latest, and revert
operations with real-time status updates and comprehensive error handling.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from shared.models import SyncOperation, OperationType, OperationStatus, Endpoint
from server.core.sync_coordinator import SyncCoordinator
from server.api.endpoints import authenticate_endpoint
from server.database.orm import ValidationError, NotFoundError

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models
class SyncOperationRequest(BaseModel):
    """Base request model for sync operations."""
    pass


class SyncOperationResponse(BaseModel):
    """Response model for sync operations."""
    operation_id: str
    endpoint_id: str
    pool_id: str
    operation_type: str
    status: str
    details: Dict[str, Any]
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class OperationStatusResponse(BaseModel):
    """Response model for operation status queries."""
    operation_id: str
    status: str
    progress: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    completed_at: Optional[str] = None


class OperationListResponse(BaseModel):
    """Response model for operation lists."""
    operations: List[SyncOperationResponse]
    total_count: int


# WebSocket connection manager for real-time updates
class ConnectionManager:
    """Manages WebSocket connections for real-time operation updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, endpoint_id: str):
        """Accept a WebSocket connection for an endpoint."""
        await websocket.accept()
        if endpoint_id not in self.active_connections:
            self.active_connections[endpoint_id] = []
        self.active_connections[endpoint_id].append(websocket)
        logger.info(f"WebSocket connected for endpoint: {endpoint_id}")
    
    def disconnect(self, websocket: WebSocket, endpoint_id: str):
        """Remove a WebSocket connection."""
        if endpoint_id in self.active_connections:
            if websocket in self.active_connections[endpoint_id]:
                self.active_connections[endpoint_id].remove(websocket)
            if not self.active_connections[endpoint_id]:
                del self.active_connections[endpoint_id]
        logger.info(f"WebSocket disconnected for endpoint: {endpoint_id}")
    
    async def send_operation_update(self, endpoint_id: str, operation_data: Dict[str, Any]):
        """Send operation update to all connections for an endpoint."""
        if endpoint_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[endpoint_id]:
                try:
                    await connection.send_json(operation_data)
                except Exception as e:
                    logger.warning(f"Failed to send update to WebSocket: {e}")
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for connection in disconnected:
                self.disconnect(connection, endpoint_id)


# Global connection manager instance
connection_manager = ConnectionManager()


# Dependency to get sync coordinator
async def get_sync_coordinator(request: Request) -> SyncCoordinator:
    """Get sync coordinator from app state."""
    return request.app.state.sync_coordinator


def operation_to_response(operation: SyncOperation) -> SyncOperationResponse:
    """Convert SyncOperation model to response format."""
    return SyncOperationResponse(
        operation_id=operation.id,
        endpoint_id=operation.endpoint_id,
        pool_id=operation.pool_id,
        operation_type=operation.operation_type.value,
        status=operation.status.value,
        details=operation.details,
        created_at=operation.created_at.isoformat(),
        completed_at=operation.completed_at.isoformat() if operation.completed_at else None,
        error_message=operation.error_message
    )


@router.post("/sync/{endpoint_id}/sync-to-latest", response_model=SyncOperationResponse)
async def sync_to_latest(
    endpoint_id: str,
    request: SyncOperationRequest,
    current_endpoint: Endpoint = Depends(authenticate_endpoint),
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
):
    """
    Sync endpoint to the latest pool state.
    
    This endpoint triggers a synchronization operation that updates all packages
    on the endpoint to match the latest target state defined for its pool.
    """
    # Verify endpoint can only sync itself
    if current_endpoint.id != endpoint_id:
        raise HTTPException(status_code=403, detail="Can only sync own endpoint")
    
    try:
        logger.info(f"Initiating sync-to-latest for endpoint: {endpoint_id}")
        
        operation = await sync_coordinator.sync_to_latest(endpoint_id)
        
        # Send real-time update
        await connection_manager.send_operation_update(endpoint_id, {
            "type": "operation_started",
            "operation": operation_to_response(operation).dict()
        })
        
        logger.info(f"Sync operation created: {operation.id}")
        return operation_to_response(operation)
        
    except ValidationError as e:
        logger.warning(f"Validation error in sync-to-latest: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in sync-to-latest for endpoint {endpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Sync operation failed: {str(e)}")


@router.post("/sync/{endpoint_id}/set-as-latest", response_model=SyncOperationResponse)
async def set_as_latest(
    endpoint_id: str,
    request: SyncOperationRequest,
    current_endpoint: Endpoint = Depends(authenticate_endpoint),
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
):
    """
    Set endpoint's current state as the pool's latest target state.
    
    This endpoint captures the current package state of the endpoint and
    sets it as the new synchronization target for all endpoints in the pool.
    """
    # Verify endpoint can only set its own state as latest
    if current_endpoint.id != endpoint_id:
        raise HTTPException(status_code=403, detail="Can only set own endpoint as latest")
    
    try:
        logger.info(f"Initiating set-as-latest for endpoint: {endpoint_id}")
        
        operation = await sync_coordinator.set_as_latest(endpoint_id)
        
        # Send real-time update
        await connection_manager.send_operation_update(endpoint_id, {
            "type": "operation_started",
            "operation": operation_to_response(operation).dict()
        })
        
        logger.info(f"Set-as-latest operation created: {operation.id}")
        return operation_to_response(operation)
        
    except ValidationError as e:
        logger.warning(f"Validation error in set-as-latest: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in set-as-latest for endpoint {endpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Set-as-latest operation failed: {str(e)}")


@router.post("/sync/{endpoint_id}/revert", response_model=SyncOperationResponse)
async def revert_to_previous(
    endpoint_id: str,
    request: SyncOperationRequest,
    current_endpoint: Endpoint = Depends(authenticate_endpoint),
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
):
    """
    Revert endpoint to its previous package state.
    
    This endpoint reverts the endpoint's packages to the previous known state,
    effectively undoing the last synchronization or package changes.
    """
    # Verify endpoint can only revert itself
    if current_endpoint.id != endpoint_id:
        raise HTTPException(status_code=403, detail="Can only revert own endpoint")
    
    try:
        logger.info(f"Initiating revert for endpoint: {endpoint_id}")
        
        operation = await sync_coordinator.revert_to_previous(endpoint_id)
        
        # Send real-time update
        await connection_manager.send_operation_update(endpoint_id, {
            "type": "operation_started",
            "operation": operation_to_response(operation).dict()
        })
        
        logger.info(f"Revert operation created: {operation.id}")
        return operation_to_response(operation)
        
    except ValidationError as e:
        logger.warning(f"Validation error in revert: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in revert for endpoint {endpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Revert operation failed: {str(e)}")


@router.get("/sync/operations/{operation_id}", response_model=OperationStatusResponse)
async def get_operation_status(
    operation_id: str,
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
):
    """
    Get the current status of a synchronization operation.
    
    This endpoint provides detailed status information about a specific
    synchronization operation, including progress and error details.
    """
    try:
        operation = await sync_coordinator.get_operation_status(operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail="Operation not found")
        
        # Calculate progress information
        progress = None
        if operation.status == OperationStatus.IN_PROGRESS:
            progress = {
                "stage": operation.details.get("current_stage", "processing"),
                "percentage": operation.details.get("progress_percentage", 0),
                "current_action": operation.details.get("current_action", "Processing...")
            }
        elif operation.status == OperationStatus.COMPLETED:
            progress = {
                "stage": "completed",
                "percentage": 100,
                "current_action": "Operation completed successfully"
            }
        elif operation.status == OperationStatus.FAILED:
            progress = {
                "stage": "failed",
                "percentage": 0,
                "current_action": f"Operation failed: {operation.error_message or 'Unknown error'}"
            }
        
        return OperationStatusResponse(
            operation_id=operation.id,
            status=operation.status.value,
            progress=progress,
            error_message=operation.error_message,
            completed_at=operation.completed_at.isoformat() if operation.completed_at else None
        )
        
    except Exception as e:
        logger.error(f"Error getting operation status for {operation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get operation status: {str(e)}")


@router.post("/sync/operations/{operation_id}/cancel")
async def cancel_operation(
    operation_id: str,
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
):
    """
    Cancel a pending synchronization operation.
    
    This endpoint cancels a synchronization operation that is still pending.
    Operations that are already in progress cannot be cancelled.
    """
    try:
        success = await sync_coordinator.cancel_operation(operation_id)
        if not success:
            raise HTTPException(status_code=400, detail="Operation cannot be cancelled")
        
        # Get the operation to send update
        operation = await sync_coordinator.get_operation_status(operation_id)
        if operation:
            await connection_manager.send_operation_update(operation.endpoint_id, {
                "type": "operation_cancelled",
                "operation_id": operation_id
            })
        
        return {"message": "Operation cancelled successfully"}
        
    except Exception as e:
        logger.error(f"Error cancelling operation {operation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel operation: {str(e)}")


@router.get("/sync/{endpoint_id}/operations", response_model=OperationListResponse)
async def get_endpoint_operations(
    endpoint_id: str,
    limit: int = 10,
    current_endpoint: Endpoint = Depends(authenticate_endpoint),
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
):
    """
    Get recent synchronization operations for an endpoint.
    
    This endpoint returns a list of recent synchronization operations
    for the specified endpoint, including their status and details.
    """
    # Verify endpoint can only view its own operations
    if current_endpoint.id != endpoint_id:
        raise HTTPException(status_code=403, detail="Can only view own endpoint operations")
    
    try:
        operations = await sync_coordinator.get_endpoint_operations(endpoint_id, limit)
        
        return OperationListResponse(
            operations=[operation_to_response(op) for op in operations],
            total_count=len(operations)
        )
        
    except Exception as e:
        logger.error(f"Error getting operations for endpoint {endpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get operations: {str(e)}")


@router.get("/sync/pools/{pool_id}/operations", response_model=OperationListResponse)
async def get_pool_operations(
    pool_id: str,
    limit: int = 20,
    sync_coordinator: SyncCoordinator = Depends(get_sync_coordinator)
):
    """
    Get recent synchronization operations for a pool.
    
    This endpoint returns a list of recent synchronization operations
    across all endpoints in the specified pool.
    """
    try:
        operations = await sync_coordinator.get_pool_operations(pool_id, limit)
        
        return OperationListResponse(
            operations=[operation_to_response(op) for op in operations],
            total_count=len(operations)
        )
        
    except Exception as e:
        logger.error(f"Error getting operations for pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pool operations: {str(e)}")


@router.websocket("/sync/{endpoint_id}/status")
async def websocket_operation_status(websocket: WebSocket, endpoint_id: str):
    """
    WebSocket endpoint for real-time operation status updates.
    
    This endpoint provides real-time updates about synchronization operations
    for a specific endpoint, including progress updates and completion notifications.
    """
    try:
        await connection_manager.connect(websocket, endpoint_id)
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "endpoint_id": endpoint_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages (ping/pong or status requests)
                data = await websocket.receive_json()
                
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                elif data.get("type") == "get_status":
                    # Send current operation status if any
                    # This would require tracking active operations per endpoint
                    await websocket.send_json({
                        "type": "status_response",
                        "endpoint_id": endpoint_id,
                        "active_operations": [],  # Would be populated from sync coordinator
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket for endpoint {endpoint_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error for endpoint {endpoint_id}: {e}")
    finally:
        connection_manager.disconnect(websocket, endpoint_id)


# Health check endpoint for sync service
@router.get("/sync/health")
async def sync_health_check():
    """Health check endpoint for synchronization service."""
    return {
        "status": "healthy",
        "service": "sync-operations",
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(connection_manager.active_connections)
    }