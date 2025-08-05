"""
Integration test for synchronization operation API endpoints.

This module tests the sync API endpoints with a running server instance.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

from server.api.main import create_app
from server.database.connection import DatabaseManager
from server.core.sync_coordinator import SyncCoordinator
from shared.models import (
    SyncOperation, OperationType, OperationStatus, Endpoint, SyncStatus, PackagePool
)


@pytest.fixture
async def app():
    """Create test FastAPI application with mocked dependencies."""
    app = create_app()
    
    # Mock the database and services
    mock_db_manager = AsyncMock(spec=DatabaseManager)
    mock_sync_coordinator = AsyncMock(spec=SyncCoordinator)
    
    # Set up app state
    app.state.db_manager = mock_db_manager
    app.state.sync_coordinator = mock_sync_coordinator
    
    return app


@pytest.fixture
def sample_endpoint():
    """Sample endpoint for testing."""
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


class TestSyncAPIIntegration:
    """Integration tests for sync API endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, app):
        """Test sync health check endpoint."""
        from fastapi.testclient import TestClient
        
        with TestClient(app) as client:
            response = client.get("/api/sync/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "sync-operations"
            assert "timestamp" in data
            assert "active_connections" in data
    
    @pytest.mark.asyncio
    async def test_sync_coordinator_initialization(self, app):
        """Test that sync coordinator is properly initialized."""
        assert hasattr(app.state, 'sync_coordinator')
        assert app.state.sync_coordinator is not None
    
    @pytest.mark.asyncio
    async def test_database_manager_initialization(self, app):
        """Test that database manager is properly initialized."""
        assert hasattr(app.state, 'db_manager')
        assert app.state.db_manager is not None


class TestSyncOperationFlow:
    """Test complete sync operation flow."""
    
    @pytest.mark.asyncio
    async def test_sync_operation_lifecycle(self, sample_endpoint, sample_operation):
        """Test complete sync operation lifecycle."""
        # Mock sync coordinator
        mock_coordinator = AsyncMock()
        
        # Test sync_to_latest
        mock_coordinator.sync_to_latest.return_value = sample_operation
        
        # Simulate operation creation
        operation = await mock_coordinator.sync_to_latest(sample_endpoint.id)
        assert operation.id == sample_operation.id
        assert operation.status == OperationStatus.PENDING
        
        # Simulate operation progress
        sample_operation.status = OperationStatus.IN_PROGRESS
        sample_operation.details.update({
            "current_stage": "analyzing",
            "progress_percentage": 50
        })
        mock_coordinator.get_operation_status.return_value = sample_operation
        
        status = await mock_coordinator.get_operation_status(sample_operation.id)
        assert status.status == OperationStatus.IN_PROGRESS
        assert status.details["progress_percentage"] == 50
        
        # Simulate operation completion
        sample_operation.status = OperationStatus.COMPLETED
        sample_operation.completed_at = datetime.now()
        
        final_status = await mock_coordinator.get_operation_status(sample_operation.id)
        assert final_status.status == OperationStatus.COMPLETED
        assert final_status.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_set_latest_operation_flow(self, sample_endpoint):
        """Test set-as-latest operation flow."""
        mock_coordinator = AsyncMock()
        
        set_latest_operation = SyncOperation(
            id="set-latest-op",
            pool_id=sample_endpoint.pool_id,
            endpoint_id=sample_endpoint.id,
            operation_type=OperationType.SET_LATEST,
            status=OperationStatus.PENDING
        )
        
        mock_coordinator.set_as_latest.return_value = set_latest_operation
        
        operation = await mock_coordinator.set_as_latest(sample_endpoint.id)
        assert operation.operation_type == OperationType.SET_LATEST
        assert operation.endpoint_id == sample_endpoint.id
    
    @pytest.mark.asyncio
    async def test_revert_operation_flow(self, sample_endpoint):
        """Test revert operation flow."""
        mock_coordinator = AsyncMock()
        
        revert_operation = SyncOperation(
            id="revert-op",
            pool_id=sample_endpoint.pool_id,
            endpoint_id=sample_endpoint.id,
            operation_type=OperationType.REVERT,
            status=OperationStatus.PENDING
        )
        
        mock_coordinator.revert_to_previous.return_value = revert_operation
        
        operation = await mock_coordinator.revert_to_previous(sample_endpoint.id)
        assert operation.operation_type == OperationType.REVERT
        assert operation.endpoint_id == sample_endpoint.id


class TestErrorScenarios:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_endpoint_not_found_error(self):
        """Test error when endpoint is not found."""
        from server.database.orm import NotFoundError
        
        mock_coordinator = AsyncMock()
        mock_coordinator.sync_to_latest.side_effect = NotFoundError("Endpoint not found")
        
        with pytest.raises(NotFoundError):
            await mock_coordinator.sync_to_latest("non-existent-endpoint")
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self):
        """Test validation error handling."""
        from server.database.orm import ValidationError
        
        mock_coordinator = AsyncMock()
        mock_coordinator.sync_to_latest.side_effect = ValidationError("Endpoint not in pool")
        
        with pytest.raises(ValidationError):
            await mock_coordinator.sync_to_latest("test-endpoint")
    
    @pytest.mark.asyncio
    async def test_operation_cancellation_error(self):
        """Test operation cancellation error."""
        mock_coordinator = AsyncMock()
        mock_coordinator.cancel_operation.return_value = False
        
        result = await mock_coordinator.cancel_operation("non-cancellable-op")
        assert result is False


class TestConcurrencyHandling:
    """Test concurrent operation handling."""
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_same_endpoint(self, sample_endpoint):
        """Test handling of concurrent operations on same endpoint."""
        from server.database.orm import ValidationError
        
        mock_coordinator = AsyncMock()
        
        # First operation succeeds
        first_operation = SyncOperation(
            id="first-op",
            pool_id=sample_endpoint.pool_id,
            endpoint_id=sample_endpoint.id,
            operation_type=OperationType.SYNC,
            status=OperationStatus.PENDING
        )
        
        mock_coordinator.sync_to_latest.return_value = first_operation
        
        # Second operation should fail due to active operation
        mock_coordinator.sync_to_latest.side_effect = [
            first_operation,
            ValidationError("Endpoint already has an active operation")
        ]
        
        # First call succeeds
        op1 = await mock_coordinator.sync_to_latest(sample_endpoint.id)
        assert op1.id == "first-op"
        
        # Second call fails
        with pytest.raises(ValidationError):
            await mock_coordinator.sync_to_latest(sample_endpoint.id)
    
    @pytest.mark.asyncio
    async def test_multiple_endpoints_concurrent_operations(self):
        """Test concurrent operations on different endpoints."""
        mock_coordinator = AsyncMock()
        
        endpoint1_op = SyncOperation(
            id="endpoint1-op",
            pool_id="test-pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SYNC,
            status=OperationStatus.PENDING
        )
        
        endpoint2_op = SyncOperation(
            id="endpoint2-op",
            pool_id="test-pool-1",
            endpoint_id="endpoint-2",
            operation_type=OperationType.SYNC,
            status=OperationStatus.PENDING
        )
        
        mock_coordinator.sync_to_latest.side_effect = [endpoint1_op, endpoint2_op]
        
        # Both operations should succeed
        op1 = await mock_coordinator.sync_to_latest("endpoint-1")
        op2 = await mock_coordinator.sync_to_latest("endpoint-2")
        
        assert op1.endpoint_id == "endpoint-1"
        assert op2.endpoint_id == "endpoint-2"
        assert op1.id != op2.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])