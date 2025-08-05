"""
Test suite for synchronization operation API endpoints.

This module tests the sync API endpoints including sync, set-latest, revert
operations, real-time status updates, and error handling.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request

from server.api.sync import (
    router, connection_manager, operation_to_response, 
    sync_to_latest, set_as_latest, revert_to_previous,
    get_operation_status, cancel_operation
)
from shared.models import (
    SyncOperation, OperationType, OperationStatus, Endpoint, SyncStatus
)
from server.database.orm import ValidationError


@pytest.fixture
def mock_app():
    """Create mock FastAPI app with state."""
    app = MagicMock()
    app.state = MagicMock()
    app.state.sync_coordinator = AsyncMock()
    app.state.db_manager = AsyncMock()
    return app


@pytest.fixture
def mock_request(mock_app):
    """Create mock request with app state."""
    request = MagicMock(spec=Request)
    request.app = mock_app
    return request


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


class TestSyncOperationEndpoints:
    """Test sync operation endpoints."""
    
    @patch('server.api.sync.authenticate_endpoint')
    @patch('server.api.sync.get_sync_coordinator')
    def test_sync_to_latest_success(self, mock_get_coordinator, mock_auth, 
                                   client, mock_sync_coordinator, mock_endpoint, sample_operation):
        """Test successful sync-to-latest operation."""
        # Setup mocks
        mock_auth.return_value = mock_endpoint
        mock_get_coordinator.return_value = mock_sync_coordinator
        mock_sync_coordinator.sync_to_latest.return_value = sample_operation
        
        # Make request
        response = client.post(
            f"/api/sync/{mock_endpoint.id}/sync-to-latest",
            json={},
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["operation_id"] == sample_operation.id
        assert data["endpoint_id"] == sample_operation.endpoint_id
        assert data["operation_type"] == "sync"
        assert data["status"] == "pending"
        
        # Verify coordinator was called
        mock_sync_coordinator.sync_to_latest.assert_called_once_with(mock_endpoint.id)
    
    @patch('server.api.sync.authenticate_endpoint')
    @patch('server.api.sync.get_sync_coordinator')
    def test_sync_to_latest_wrong_endpoint(self, mock_get_coordinator, mock_auth, 
                                          client, mock_sync_coordinator, mock_endpoint):
        """Test sync-to-latest with wrong endpoint ID."""
        # Setup mocks
        mock_auth.return_value = mock_endpoint
        mock_get_coordinator.return_value = mock_sync_coordinator
        
        # Make request with different endpoint ID
        response = client.post(
            "/api/sync/different-endpoint/sync-to-latest",
            json={},
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Verify forbidden response
        assert response.status_code == 403
        assert "Can only sync own endpoint" in response.json()["detail"]
    
    @patch('server.api.sync.authenticate_endpoint')
    @patch('server.api.sync.get_sync_coordinator')
    def test_sync_to_latest_validation_error(self, mock_get_coordinator, mock_auth, 
                                            client, mock_sync_coordinator, mock_endpoint):
        """Test sync-to-latest with validation error."""
        # Setup mocks
        mock_auth.return_value = mock_endpoint
        mock_get_coordinator.return_value = mock_sync_coordinator
        mock_sync_coordinator.sync_to_latest.side_effect = ValidationError("Endpoint not in pool")
        
        # Make request
        response = client.post(
            f"/api/sync/{mock_endpoint.id}/sync-to-latest",
            json={},
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Verify error response
        assert response.status_code == 400
        assert "Endpoint not in pool" in response.json()["detail"]
    
    @patch('server.api.sync.authenticate_endpoint')
    @patch('server.api.sync.get_sync_coordinator')
    def test_set_as_latest_success(self, mock_get_coordinator, mock_auth, 
                                  client, mock_sync_coordinator, mock_endpoint):
        """Test successful set-as-latest operation."""
        # Setup mocks
        mock_auth.return_value = mock_endpoint
        mock_get_coordinator.return_value = mock_sync_coordinator
        
        set_latest_operation = SyncOperation(
            id="set-latest-op-1",
            pool_id="test-pool-1",
            endpoint_id="test-endpoint-1",
            operation_type=OperationType.SET_LATEST,
            status=OperationStatus.PENDING
        )
        mock_sync_coordinator.set_as_latest.return_value = set_latest_operation
        
        # Make request
        response = client.post(
            f"/api/sync/{mock_endpoint.id}/set-as-latest",
            json={},
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["operation_type"] == "set_latest"
        assert data["status"] == "pending"
        
        # Verify coordinator was called
        mock_sync_coordinator.set_as_latest.assert_called_once_with(mock_endpoint.id)
    
    @patch('server.api.sync.authenticate_endpoint')
    @patch('server.api.sync.get_sync_coordinator')
    def test_revert_to_previous_success(self, mock_get_coordinator, mock_auth, 
                                       client, mock_sync_coordinator, mock_endpoint):
        """Test successful revert operation."""
        # Setup mocks
        mock_auth.return_value = mock_endpoint
        mock_get_coordinator.return_value = mock_sync_coordinator
        
        revert_operation = SyncOperation(
            id="revert-op-1",
            pool_id="test-pool-1",
            endpoint_id="test-endpoint-1",
            operation_type=OperationType.REVERT,
            status=OperationStatus.PENDING
        )
        mock_sync_coordinator.revert_to_previous.return_value = revert_operation
        
        # Make request
        response = client.post(
            f"/api/sync/{mock_endpoint.id}/revert",
            json={},
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["operation_type"] == "revert"
        assert data["status"] == "pending"
        
        # Verify coordinator was called
        mock_sync_coordinator.revert_to_previous.assert_called_once_with(mock_endpoint.id)


class TestOperationStatusEndpoints:
    """Test operation status and management endpoints."""
    
    @patch('server.api.sync.get_sync_coordinator')
    def test_get_operation_status_success(self, mock_get_coordinator, 
                                         client, mock_sync_coordinator, sample_operation):
        """Test getting operation status."""
        # Setup mocks
        mock_get_coordinator.return_value = mock_sync_coordinator
        sample_operation.status = OperationStatus.IN_PROGRESS
        sample_operation.details = {
            "current_stage": "analyzing",
            "progress_percentage": 45,
            "current_action": "Analyzing package differences"
        }
        mock_sync_coordinator.get_operation_status.return_value = sample_operation
        
        # Make request
        response = client.get(f"/api/sync/operations/{sample_operation.id}")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["operation_id"] == sample_operation.id
        assert data["status"] == "in_progress"
        assert data["progress"]["stage"] == "analyzing"
        assert data["progress"]["percentage"] == 45
        assert "Analyzing package differences" in data["progress"]["current_action"]
    
    @patch('server.api.sync.get_sync_coordinator')
    def test_get_operation_status_not_found(self, mock_get_coordinator, 
                                           client, mock_sync_coordinator):
        """Test getting status for non-existent operation."""
        # Setup mocks
        mock_get_coordinator.return_value = mock_sync_coordinator
        mock_sync_coordinator.get_operation_status.return_value = None
        
        # Make request
        response = client.get("/api/sync/operations/non-existent")
        
        # Verify response
        assert response.status_code == 404
        assert "Operation not found" in response.json()["detail"]
    
    @patch('server.api.sync.get_sync_coordinator')
    def test_cancel_operation_success(self, mock_get_coordinator, 
                                     client, mock_sync_coordinator, sample_operation):
        """Test cancelling an operation."""
        # Setup mocks
        mock_get_coordinator.return_value = mock_sync_coordinator
        mock_sync_coordinator.cancel_operation.return_value = True
        mock_sync_coordinator.get_operation_status.return_value = sample_operation
        
        # Make request
        response = client.post(f"/api/sync/operations/{sample_operation.id}/cancel")
        
        # Verify response
        assert response.status_code == 200
        assert "cancelled successfully" in response.json()["message"]
        
        # Verify coordinator was called
        mock_sync_coordinator.cancel_operation.assert_called_once_with(sample_operation.id)
    
    @patch('server.api.sync.get_sync_coordinator')
    def test_cancel_operation_failed(self, mock_get_coordinator, 
                                    client, mock_sync_coordinator):
        """Test cancelling an operation that cannot be cancelled."""
        # Setup mocks
        mock_get_coordinator.return_value = mock_sync_coordinator
        mock_sync_coordinator.cancel_operation.return_value = False
        
        # Make request
        response = client.post("/api/sync/operations/test-op/cancel")
        
        # Verify response
        assert response.status_code == 400
        assert "cannot be cancelled" in response.json()["detail"]


class TestOperationListEndpoints:
    """Test operation listing endpoints."""
    
    @patch('server.api.sync.authenticate_endpoint')
    @patch('server.api.sync.get_sync_coordinator')
    def test_get_endpoint_operations(self, mock_get_coordinator, mock_auth, 
                                    client, mock_sync_coordinator, mock_endpoint):
        """Test getting operations for an endpoint."""
        # Setup mocks
        mock_auth.return_value = mock_endpoint
        mock_get_coordinator.return_value = mock_sync_coordinator
        
        operations = [
            SyncOperation(
                id="op1",
                pool_id="test-pool-1",
                endpoint_id="test-endpoint-1",
                operation_type=OperationType.SYNC,
                status=OperationStatus.COMPLETED
            ),
            SyncOperation(
                id="op2",
                pool_id="test-pool-1",
                endpoint_id="test-endpoint-1",
                operation_type=OperationType.SET_LATEST,
                status=OperationStatus.PENDING
            )
        ]
        mock_sync_coordinator.get_endpoint_operations.return_value = operations
        
        # Make request
        response = client.get(
            f"/api/sync/{mock_endpoint.id}/operations",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["operations"]) == 2
        assert data["operations"][0]["operation_id"] == "op1"
        assert data["operations"][1]["operation_id"] == "op2"
    
    @patch('server.api.sync.get_sync_coordinator')
    def test_get_pool_operations(self, mock_get_coordinator, 
                                client, mock_sync_coordinator):
        """Test getting operations for a pool."""
        # Setup mocks
        mock_get_coordinator.return_value = mock_sync_coordinator
        
        operations = [
            SyncOperation(
                id="pool-op1",
                pool_id="test-pool-1",
                endpoint_id="endpoint1",
                operation_type=OperationType.SYNC,
                status=OperationStatus.COMPLETED
            )
        ]
        mock_sync_coordinator.get_pool_operations.return_value = operations
        
        # Make request
        response = client.get("/api/sync/pools/test-pool-1/operations")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["operations"][0]["pool_id"] == "test-pool-1"


class TestConnectionManager:
    """Test WebSocket connection manager."""
    
    def test_connection_manager_connect_disconnect(self):
        """Test WebSocket connection and disconnection."""
        manager = connection_manager
        mock_websocket = MagicMock()
        endpoint_id = "test-endpoint"
        
        # Test connection
        asyncio.run(manager.connect(mock_websocket, endpoint_id))
        assert endpoint_id in manager.active_connections
        assert mock_websocket in manager.active_connections[endpoint_id]
        
        # Test disconnection
        manager.disconnect(mock_websocket, endpoint_id)
        assert endpoint_id not in manager.active_connections
    
    def test_connection_manager_send_update(self):
        """Test sending updates through WebSocket."""
        manager = connection_manager
        mock_websocket = AsyncMock()
        endpoint_id = "test-endpoint"
        
        async def test_send():
            await manager.connect(mock_websocket, endpoint_id)
            
            update_data = {
                "type": "operation_started",
                "operation_id": "test-op"
            }
            
            await manager.send_operation_update(endpoint_id, update_data)
            mock_websocket.send_json.assert_called_once_with(update_data)
        
        asyncio.run(test_send())


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_sync_health_check(self, client):
        """Test sync service health check."""
        response = client.get("/api/sync/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sync-operations"
        assert "timestamp" in data
        assert "active_connections" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])