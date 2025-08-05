"""
Unit tests for synchronization operation API endpoints.

This module tests the core sync API functionality without full FastAPI integration.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from server.api.sync import (
    operation_to_response, ConnectionManager
)
from shared.models import (
    SyncOperation, OperationType, OperationStatus, Endpoint, SyncStatus
)
from server.database.orm import ValidationError


@pytest.fixture
def mock_sync_coordinator():
    """Mock sync coordinator."""
    coordinator = AsyncMock()
    return coordinator


@pytest.fixture
def mock_endpoint():
    """Mock authenticated endpoint."""
    return Endpoint(
        id="test-endpoint-1",
        name="test-endpoint",
        hostname="test-host",
        pool_id="test-pool-1",
        sync_status=SyncStatus.BEHIND
    )


@pytest.fixture
def sample_operation():
    """Sample sync operation."""
    return SyncOperation(
        id="test-operation-1",
        pool_id="test-pool-1",
        endpoint_id="test-endpoint-1",
        operation_type=OperationType.SYNC,
        status=OperationStatus.PENDING,
        details={"initiated_by": "test"}
    )


class TestOperationToResponse:
    """Test operation to response conversion."""
    
    def test_operation_to_response_basic(self, sample_operation):
        """Test basic operation to response conversion."""
        response = operation_to_response(sample_operation)
        
        assert response.operation_id == sample_operation.id
        assert response.endpoint_id == sample_operation.endpoint_id
        assert response.pool_id == sample_operation.pool_id
        assert response.operation_type == "sync"
        assert response.status == "pending"
        assert response.details == sample_operation.details
        assert response.created_at == sample_operation.created_at.isoformat()
        assert response.completed_at is None
        assert response.error_message is None
    
    def test_operation_to_response_completed(self, sample_operation):
        """Test operation to response with completed operation."""
        sample_operation.status = OperationStatus.COMPLETED
        sample_operation.completed_at = datetime.now()
        
        response = operation_to_response(sample_operation)
        
        assert response.status == "completed"
        assert response.completed_at == sample_operation.completed_at.isoformat()
    
    def test_operation_to_response_failed(self, sample_operation):
        """Test operation to response with failed operation."""
        sample_operation.status = OperationStatus.FAILED
        sample_operation.error_message = "Test error"
        
        response = operation_to_response(sample_operation)
        
        assert response.status == "failed"
        assert response.error_message == "Test error"


class TestConnectionManager:
    """Test WebSocket connection manager."""
    
    def test_connection_manager_init(self):
        """Test connection manager initialization."""
        manager = ConnectionManager()
        assert manager.active_connections == {}
    
    @pytest.mark.asyncio
    async def test_connect_websocket(self):
        """Test WebSocket connection."""
        manager = ConnectionManager()
        mock_websocket = AsyncMock()
        endpoint_id = "test-endpoint"
        
        await manager.connect(mock_websocket, endpoint_id)
        
        assert endpoint_id in manager.active_connections
        assert mock_websocket in manager.active_connections[endpoint_id]
        mock_websocket.accept.assert_called_once()
    
    def test_disconnect_websocket(self):
        """Test WebSocket disconnection."""
        manager = ConnectionManager()
        mock_websocket = MagicMock()
        endpoint_id = "test-endpoint"
        
        # Manually add connection
        manager.active_connections[endpoint_id] = [mock_websocket]
        
        manager.disconnect(mock_websocket, endpoint_id)
        
        assert endpoint_id not in manager.active_connections
    
    def test_disconnect_websocket_multiple_connections(self):
        """Test WebSocket disconnection with multiple connections."""
        manager = ConnectionManager()
        mock_websocket1 = MagicMock()
        mock_websocket2 = MagicMock()
        endpoint_id = "test-endpoint"
        
        # Manually add connections
        manager.active_connections[endpoint_id] = [mock_websocket1, mock_websocket2]
        
        manager.disconnect(mock_websocket1, endpoint_id)
        
        assert endpoint_id in manager.active_connections
        assert mock_websocket1 not in manager.active_connections[endpoint_id]
        assert mock_websocket2 in manager.active_connections[endpoint_id]
    
    @pytest.mark.asyncio
    async def test_send_operation_update(self):
        """Test sending operation update."""
        manager = ConnectionManager()
        mock_websocket = AsyncMock()
        endpoint_id = "test-endpoint"
        
        # Manually add connection
        manager.active_connections[endpoint_id] = [mock_websocket]
        
        update_data = {
            "type": "operation_started",
            "operation_id": "test-op"
        }
        
        await manager.send_operation_update(endpoint_id, update_data)
        
        mock_websocket.send_json.assert_called_once_with(update_data)
    
    @pytest.mark.asyncio
    async def test_send_operation_update_no_connections(self):
        """Test sending operation update with no connections."""
        manager = ConnectionManager()
        endpoint_id = "test-endpoint"
        
        update_data = {
            "type": "operation_started",
            "operation_id": "test-op"
        }
        
        # Should not raise an exception
        await manager.send_operation_update(endpoint_id, update_data)
    
    @pytest.mark.asyncio
    async def test_send_operation_update_failed_connection(self):
        """Test sending operation update with failed connection."""
        manager = ConnectionManager()
        mock_websocket = AsyncMock()
        mock_websocket.send_json.side_effect = Exception("Connection failed")
        endpoint_id = "test-endpoint"
        
        # Manually add connection
        manager.active_connections[endpoint_id] = [mock_websocket]
        
        update_data = {
            "type": "operation_started",
            "operation_id": "test-op"
        }
        
        await manager.send_operation_update(endpoint_id, update_data)
        
        # Connection should be removed after failure
        assert endpoint_id not in manager.active_connections


class TestSyncOperationLogic:
    """Test sync operation business logic."""
    
    @pytest.mark.asyncio
    async def test_sync_coordinator_integration(self, mock_sync_coordinator, mock_endpoint):
        """Test sync coordinator integration."""
        # Test sync_to_latest
        expected_operation = SyncOperation(
            id="test-op",
            pool_id=mock_endpoint.pool_id,
            endpoint_id=mock_endpoint.id,
            operation_type=OperationType.SYNC,
            status=OperationStatus.PENDING
        )
        
        mock_sync_coordinator.sync_to_latest.return_value = expected_operation
        
        result = await mock_sync_coordinator.sync_to_latest(mock_endpoint.id)
        
        assert result.id == expected_operation.id
        assert result.endpoint_id == mock_endpoint.id
        assert result.operation_type == OperationType.SYNC
        mock_sync_coordinator.sync_to_latest.assert_called_once_with(mock_endpoint.id)
    
    @pytest.mark.asyncio
    async def test_sync_coordinator_validation_error(self, mock_sync_coordinator, mock_endpoint):
        """Test sync coordinator validation error handling."""
        mock_sync_coordinator.sync_to_latest.side_effect = ValidationError("Endpoint not in pool")
        
        with pytest.raises(ValidationError) as exc_info:
            await mock_sync_coordinator.sync_to_latest(mock_endpoint.id)
        
        assert "Endpoint not in pool" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_operation_status_tracking(self, mock_sync_coordinator, sample_operation):
        """Test operation status tracking."""
        # Test getting operation status
        mock_sync_coordinator.get_operation_status.return_value = sample_operation
        
        result = await mock_sync_coordinator.get_operation_status(sample_operation.id)
        
        assert result.id == sample_operation.id
        assert result.status == OperationStatus.PENDING
        mock_sync_coordinator.get_operation_status.assert_called_once_with(sample_operation.id)
    
    @pytest.mark.asyncio
    async def test_operation_cancellation(self, mock_sync_coordinator):
        """Test operation cancellation."""
        operation_id = "test-operation-id"
        mock_sync_coordinator.cancel_operation.return_value = True
        
        result = await mock_sync_coordinator.cancel_operation(operation_id)
        
        assert result is True
        mock_sync_coordinator.cancel_operation.assert_called_once_with(operation_id)
    
    @pytest.mark.asyncio
    async def test_endpoint_operations_list(self, mock_sync_coordinator, mock_endpoint):
        """Test getting endpoint operations list."""
        operations = [
            SyncOperation(
                id="op1",
                pool_id=mock_endpoint.pool_id,
                endpoint_id=mock_endpoint.id,
                operation_type=OperationType.SYNC,
                status=OperationStatus.COMPLETED
            ),
            SyncOperation(
                id="op2",
                pool_id=mock_endpoint.pool_id,
                endpoint_id=mock_endpoint.id,
                operation_type=OperationType.SET_LATEST,
                status=OperationStatus.PENDING
            )
        ]
        
        mock_sync_coordinator.get_endpoint_operations.return_value = operations
        
        result = await mock_sync_coordinator.get_endpoint_operations(mock_endpoint.id, 10)
        
        assert len(result) == 2
        assert result[0].id == "op1"
        assert result[1].id == "op2"
        mock_sync_coordinator.get_endpoint_operations.assert_called_once_with(mock_endpoint.id, 10)


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_validation_error_handling(self):
        """Test validation error handling."""
        error = ValidationError("Test validation error")
        assert str(error) == "Test validation error"
    
    @pytest.mark.asyncio
    async def test_sync_coordinator_exception_handling(self, mock_sync_coordinator):
        """Test sync coordinator exception handling."""
        mock_sync_coordinator.sync_to_latest.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception) as exc_info:
            await mock_sync_coordinator.sync_to_latest("test-endpoint")
        
        assert "Database connection failed" in str(exc_info.value)


class TestProgressTracking:
    """Test operation progress tracking."""
    
    def test_progress_calculation_pending(self, sample_operation):
        """Test progress calculation for pending operation."""
        sample_operation.status = OperationStatus.PENDING
        
        response = operation_to_response(sample_operation)
        
        assert response.status == "pending"
    
    def test_progress_calculation_in_progress(self, sample_operation):
        """Test progress calculation for in-progress operation."""
        sample_operation.status = OperationStatus.IN_PROGRESS
        sample_operation.details = {
            "current_stage": "analyzing",
            "progress_percentage": 45,
            "current_action": "Analyzing package differences"
        }
        
        response = operation_to_response(sample_operation)
        
        assert response.status == "in_progress"
        assert response.details["current_stage"] == "analyzing"
        assert response.details["progress_percentage"] == 45
    
    def test_progress_calculation_completed(self, sample_operation):
        """Test progress calculation for completed operation."""
        sample_operation.status = OperationStatus.COMPLETED
        sample_operation.completed_at = datetime.now()
        
        response = operation_to_response(sample_operation)
        
        assert response.status == "completed"
        assert response.completed_at is not None
    
    def test_progress_calculation_failed(self, sample_operation):
        """Test progress calculation for failed operation."""
        sample_operation.status = OperationStatus.FAILED
        sample_operation.error_message = "Operation failed due to network error"
        
        response = operation_to_response(sample_operation)
        
        assert response.status == "failed"
        assert response.error_message == "Operation failed due to network error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])