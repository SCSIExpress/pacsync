#!/usr/bin/env python3
"""
Unit tests for SyncCoordinator core service.

Tests synchronization coordination functionality including sync operations,
state management, conflict resolution, and rollback capabilities.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from server.core.sync_coordinator import (
    SyncCoordinator, StateManager, SyncConflict, SyncConflictType, StateSnapshot
)
from shared.models import (
    SyncOperation, SystemState, PackageState, Endpoint, PackagePool,
    OperationType, OperationStatus, SyncStatus, ConflictResolution
)
from server.database.orm import ValidationError, NotFoundError


class TestSyncConflict:
    """Test SyncConflict helper class."""
    
    def test_sync_conflict_creation(self):
        """Test creating a SyncConflict."""
        conflict = SyncConflict(
            conflict_type=SyncConflictType.VERSION_MISMATCH,
            package_name="test-package",
            details={"current": "1.0.0", "target": "2.0.0"},
            suggested_resolution="Update to version 2.0.0"
        )
        
        assert conflict.conflict_type == SyncConflictType.VERSION_MISMATCH
        assert conflict.package_name == "test-package"
        assert conflict.details == {"current": "1.0.0", "target": "2.0.0"}
        assert conflict.suggested_resolution == "Update to version 2.0.0"
        assert isinstance(conflict.timestamp, datetime)
    
    def test_sync_conflict_to_dict(self):
        """Test SyncConflict to_dict conversion."""
        conflict = SyncConflict(
            conflict_type=SyncConflictType.MISSING_PACKAGE,
            package_name="missing-pkg",
            details={"action": "install"},
            suggested_resolution="Install package"
        )
        
        result = conflict.to_dict()
        
        assert result["conflict_type"] == "missing_package"
        assert result["package_name"] == "missing-pkg"
        assert result["details"] == {"action": "install"}
        assert result["suggested_resolution"] == "Install package"
        assert "timestamp" in result


class TestStateSnapshot:
    """Test StateSnapshot helper class."""
    
    def test_state_snapshot_creation(self):
        """Test creating a StateSnapshot."""
        packages = [
            PackageState("pkg1", "1.0.0", "core", 1024),
            PackageState("pkg2", "2.0.0", "extra", 2048)
        ]
        system_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=packages,
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        snapshot = StateSnapshot(
            state_id="state-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            system_state=system_state,
            is_target=True
        )
        
        assert snapshot.state_id == "state-1"
        assert snapshot.pool_id == "pool-1"
        assert snapshot.endpoint_id == "endpoint-1"
        assert snapshot.system_state == system_state
        assert snapshot.is_target == True
        assert isinstance(snapshot.created_at, datetime)
    
    def test_state_snapshot_to_dict(self):
        """Test StateSnapshot to_dict conversion."""
        packages = [PackageState("pkg1", "1.0.0", "core", 1024)]
        system_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=packages,
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        snapshot = StateSnapshot(
            state_id="state-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            system_state=system_state
        )
        
        result = snapshot.to_dict()
        
        assert result["state_id"] == "state-1"
        assert result["pool_id"] == "pool-1"
        assert result["endpoint_id"] == "endpoint-1"
        assert result["package_count"] == 1
        assert result["pacman_version"] == "6.0.1"
        assert result["architecture"] == "x86_64"
        assert result["is_target"] == False
        assert "created_at" in result


class TestStateManager:
    """Test StateManager component."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        return MagicMock()
    
    @pytest.fixture
    def mock_state_repo(self):
        """Create mock state repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_pool_repo(self):
        """Create mock pool repository."""
        return AsyncMock()
    
    @pytest.fixture
    def state_manager(self, mock_db_manager, mock_state_repo, mock_pool_repo):
        """Create StateManager with mocked dependencies."""
        manager = StateManager(mock_db_manager)
        manager.state_repo = mock_state_repo
        manager.pool_repo = mock_pool_repo
        return manager
    
    @pytest.mark.asyncio
    async def test_save_state_success(self, state_manager, mock_state_repo):
        """Test successful state saving."""
        packages = [PackageState("pkg1", "1.0.0", "core", 1024)]
        system_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=packages,
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        # Mock endpoint repository
        with patch('server.core.sync_coordinator.EndpointRepository') as mock_endpoint_repo_class:
            mock_endpoint_repo = AsyncMock()
            mock_endpoint_repo_class.return_value = mock_endpoint_repo
            
            endpoint = Endpoint("endpoint-1", "Test Endpoint", "host1", pool_id="pool-1")
            mock_endpoint_repo.get_by_id.return_value = endpoint
            mock_state_repo.save_state.return_value = "state-1"
            
            result = await state_manager.save_state("endpoint-1", system_state)
            
            assert result == "state-1"
            mock_state_repo.save_state.assert_called_once_with("pool-1", "endpoint-1", system_state)
    
    @pytest.mark.asyncio
    async def test_save_state_endpoint_not_found(self, state_manager):
        """Test state saving when endpoint doesn't exist."""
        system_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=[],
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        with patch('server.core.sync_coordinator.EndpointRepository') as mock_endpoint_repo_class:
            mock_endpoint_repo = AsyncMock()
            mock_endpoint_repo_class.return_value = mock_endpoint_repo
            mock_endpoint_repo.get_by_id.return_value = None
            
            with pytest.raises(ValidationError, match="Endpoint .* not found"):
                await state_manager.save_state("non-existent", system_state)
    
    @pytest.mark.asyncio
    async def test_save_state_endpoint_no_pool(self, state_manager):
        """Test state saving when endpoint has no pool."""
        system_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=[],
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        with patch('server.core.sync_coordinator.EndpointRepository') as mock_endpoint_repo_class:
            mock_endpoint_repo = AsyncMock()
            mock_endpoint_repo_class.return_value = mock_endpoint_repo
            
            endpoint = Endpoint("endpoint-1", "Test Endpoint", "host1", pool_id=None)
            mock_endpoint_repo.get_by_id.return_value = endpoint
            
            with pytest.raises(ValidationError, match="not assigned to a pool"):
                await state_manager.save_state("endpoint-1", system_state)
    
    @pytest.mark.asyncio
    async def test_get_state_success(self, state_manager, mock_state_repo):
        """Test successful state retrieval."""
        expected_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=[],
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        mock_state_repo.get_state.return_value = expected_state
        
        result = await state_manager.get_state("state-1")
        
        assert result == expected_state
        mock_state_repo.get_state.assert_called_once_with("state-1")
    
    @pytest.mark.asyncio
    async def test_get_latest_state_success(self, state_manager, mock_state_repo):
        """Test successful latest state retrieval."""
        expected_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=[],
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        mock_state_repo.get_latest_target_state.return_value = expected_state
        
        result = await state_manager.get_latest_state("pool-1")
        
        assert result == expected_state
        mock_state_repo.get_latest_target_state.assert_called_once_with("pool-1")
    
    @pytest.mark.asyncio
    async def test_set_target_state_success(self, state_manager, mock_state_repo):
        """Test successful target state setting."""
        mock_state_repo.set_target_state.return_value = True
        
        result = await state_manager.set_target_state("pool-1", "state-1")
        
        assert result == True
        mock_state_repo.set_target_state.assert_called_once_with("pool-1", "state-1")


class TestSyncCoordinator:
    """Test SyncCoordinator core service."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        return MagicMock()
    
    @pytest.fixture
    def mock_operation_repo(self):
        """Create mock operation repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_endpoint_repo(self):
        """Create mock endpoint repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_pool_repo(self):
        """Create mock pool repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_state_manager(self):
        """Create mock state manager."""
        return AsyncMock()
    
    @pytest.fixture
    def sync_coordinator(self, mock_db_manager, mock_operation_repo, mock_endpoint_repo, 
                        mock_pool_repo, mock_state_manager):
        """Create SyncCoordinator with mocked dependencies."""
        coordinator = SyncCoordinator(mock_db_manager)
        coordinator.operation_repo = mock_operation_repo
        coordinator.endpoint_repo = mock_endpoint_repo
        coordinator.pool_repo = mock_pool_repo
        coordinator.state_manager = mock_state_manager
        return coordinator
    
    @pytest.mark.asyncio
    async def test_sync_to_latest_success(self, sync_coordinator, mock_endpoint_repo, 
                                         mock_pool_repo, mock_state_manager, mock_operation_repo):
        """Test successful sync to latest operation."""
        # Setup mocks
        endpoint = Endpoint("endpoint-1", "Test Endpoint", "host1", pool_id="pool-1")
        pool = PackagePool("pool-1", "Test Pool", "Description", target_state_id="state-1")
        target_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=[PackageState("pkg1", "1.0.0", "core", 1024)],
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        mock_endpoint_repo.get_by_id.return_value = endpoint
        mock_pool_repo.get_by_id.return_value = pool
        mock_state_manager.get_latest_state.return_value = target_state
        
        expected_operation = SyncOperation(
            id="op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SYNC,
            status=OperationStatus.PENDING
        )
        mock_operation_repo.create.return_value = expected_operation
        
        # Execute
        result = await sync_coordinator.sync_to_latest("endpoint-1")
        
        # Verify
        assert result == expected_operation
        mock_endpoint_repo.get_by_id.assert_called_once_with("endpoint-1")
        mock_pool_repo.get_by_id.assert_called_once_with("pool-1")
        mock_state_manager.get_latest_state.assert_called_once_with("pool-1")
        mock_operation_repo.create.assert_called_once()
        
        # Check operation details
        call_args = mock_operation_repo.create.call_args[0][0]
        assert call_args.operation_type == OperationType.SYNC
        assert call_args.pool_id == "pool-1"
        assert call_args.endpoint_id == "endpoint-1"
    
    @pytest.mark.asyncio
    async def test_sync_to_latest_endpoint_not_found(self, sync_coordinator, mock_endpoint_repo):
        """Test sync to latest when endpoint doesn't exist."""
        mock_endpoint_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError, match="Endpoint .* not found"):
            await sync_coordinator.sync_to_latest("non-existent")
    
    @pytest.mark.asyncio
    async def test_sync_to_latest_endpoint_no_pool(self, sync_coordinator, mock_endpoint_repo):
        """Test sync to latest when endpoint has no pool."""
        endpoint = Endpoint("endpoint-1", "Test Endpoint", "host1", pool_id=None)
        mock_endpoint_repo.get_by_id.return_value = endpoint
        
        with pytest.raises(ValidationError, match="not assigned to a pool"):
            await sync_coordinator.sync_to_latest("endpoint-1")
    
    @pytest.mark.asyncio
    async def test_sync_to_latest_pool_not_found(self, sync_coordinator, mock_endpoint_repo, mock_pool_repo):
        """Test sync to latest when pool doesn't exist."""
        endpoint = Endpoint("endpoint-1", "Test Endpoint", "host1", pool_id="pool-1")
        mock_endpoint_repo.get_by_id.return_value = endpoint
        mock_pool_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError, match="Pool .* not found"):
            await sync_coordinator.sync_to_latest("endpoint-1")
    
    @pytest.mark.asyncio
    async def test_sync_to_latest_no_target_state(self, sync_coordinator, mock_endpoint_repo, 
                                                 mock_pool_repo, mock_state_manager):
        """Test sync to latest when no target state is set."""
        endpoint = Endpoint("endpoint-1", "Test Endpoint", "host1", pool_id="pool-1")
        pool = PackagePool("pool-1", "Test Pool", "Description")
        
        mock_endpoint_repo.get_by_id.return_value = endpoint
        mock_pool_repo.get_by_id.return_value = pool
        mock_state_manager.get_latest_state.return_value = None
        
        with pytest.raises(ValidationError, match="No target state set"):
            await sync_coordinator.sync_to_latest("endpoint-1")
    
    @pytest.mark.asyncio
    async def test_sync_to_latest_active_operation_exists(self, sync_coordinator, mock_endpoint_repo, 
                                                         mock_pool_repo, mock_state_manager, mock_operation_repo):
        """Test sync to latest when endpoint already has active operation."""
        endpoint = Endpoint("endpoint-1", "Test Endpoint", "host1", pool_id="pool-1")
        pool = PackagePool("pool-1", "Test Pool", "Description")
        target_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=[],
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        mock_endpoint_repo.get_by_id.return_value = endpoint
        mock_pool_repo.get_by_id.return_value = pool
        mock_state_manager.get_latest_state.return_value = target_state
        
        # Set up active operation
        sync_coordinator._active_operations["endpoint-1"] = "active-op-1"
        active_operation = SyncOperation(
            id="active-op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SYNC,
            status=OperationStatus.IN_PROGRESS
        )
        mock_operation_repo.get_by_id.return_value = active_operation
        
        with pytest.raises(ValidationError, match="already has an active operation"):
            await sync_coordinator.sync_to_latest("endpoint-1")
    
    @pytest.mark.asyncio
    async def test_set_as_latest_success(self, sync_coordinator, mock_endpoint_repo, 
                                        mock_operation_repo):
        """Test successful set as latest operation."""
        endpoint = Endpoint("endpoint-1", "Test Endpoint", "host1", pool_id="pool-1")
        mock_endpoint_repo.get_by_id.return_value = endpoint
        
        expected_operation = SyncOperation(
            id="op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SET_LATEST,
            status=OperationStatus.PENDING
        )
        mock_operation_repo.create.return_value = expected_operation
        
        result = await sync_coordinator.set_as_latest("endpoint-1")
        
        assert result == expected_operation
        mock_operation_repo.create.assert_called_once()
        
        call_args = mock_operation_repo.create.call_args[0][0]
        assert call_args.operation_type == OperationType.SET_LATEST
    
    @pytest.mark.asyncio
    async def test_revert_to_previous_success(self, sync_coordinator, mock_endpoint_repo, 
                                             mock_state_manager, mock_operation_repo):
        """Test successful revert to previous operation."""
        endpoint = Endpoint("endpoint-1", "Test Endpoint", "host1", pool_id="pool-1")
        mock_endpoint_repo.get_by_id.return_value = endpoint
        
        # Mock previous states
        current_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=[PackageState("pkg1", "2.0.0", "core", 1024)],
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        previous_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=[PackageState("pkg1", "1.0.0", "core", 1024)],
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        mock_state_manager.get_endpoint_states.return_value = [current_state, previous_state]
        
        expected_operation = SyncOperation(
            id="op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.REVERT,
            status=OperationStatus.PENDING
        )
        mock_operation_repo.create.return_value = expected_operation
        
        result = await sync_coordinator.revert_to_previous("endpoint-1")
        
        assert result == expected_operation
        mock_state_manager.get_endpoint_states.assert_called_once_with("endpoint-1", limit=2)
        
        call_args = mock_operation_repo.create.call_args[0][0]
        assert call_args.operation_type == OperationType.REVERT
    
    @pytest.mark.asyncio
    async def test_revert_to_previous_no_previous_state(self, sync_coordinator, mock_endpoint_repo, 
                                                       mock_state_manager):
        """Test revert to previous when no previous state exists."""
        endpoint = Endpoint("endpoint-1", "Test Endpoint", "host1", pool_id="pool-1")
        mock_endpoint_repo.get_by_id.return_value = endpoint
        
        # Only one state available
        current_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=[],
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        mock_state_manager.get_endpoint_states.return_value = [current_state]
        
        with pytest.raises(ValidationError, match="No previous state available"):
            await sync_coordinator.revert_to_previous("endpoint-1")
    
    @pytest.mark.asyncio
    async def test_get_operation_status_success(self, sync_coordinator, mock_operation_repo):
        """Test successful operation status retrieval."""
        expected_operation = SyncOperation(
            id="op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SYNC,
            status=OperationStatus.COMPLETED
        )
        mock_operation_repo.get_by_id.return_value = expected_operation
        
        result = await sync_coordinator.get_operation_status("op-1")
        
        assert result == expected_operation
        mock_operation_repo.get_by_id.assert_called_once_with("op-1")
    
    @pytest.mark.asyncio
    async def test_cancel_operation_success(self, sync_coordinator, mock_operation_repo):
        """Test successful operation cancellation."""
        operation = SyncOperation(
            id="op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SYNC,
            status=OperationStatus.PENDING
        )
        mock_operation_repo.get_by_id.return_value = operation
        mock_operation_repo.update_status.return_value = True
        
        # Set up active operation
        sync_coordinator._active_operations["endpoint-1"] = "op-1"
        
        result = await sync_coordinator.cancel_operation("op-1")
        
        assert result == True
        mock_operation_repo.update_status.assert_called_once_with(
            "op-1", OperationStatus.FAILED, "Operation cancelled by user"
        )
        assert "endpoint-1" not in sync_coordinator._active_operations
    
    @pytest.mark.asyncio
    async def test_cancel_operation_not_found(self, sync_coordinator, mock_operation_repo):
        """Test operation cancellation when operation doesn't exist."""
        mock_operation_repo.get_by_id.return_value = None
        
        result = await sync_coordinator.cancel_operation("non-existent")
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_cancel_operation_not_pending(self, sync_coordinator, mock_operation_repo):
        """Test operation cancellation when operation is not pending."""
        operation = SyncOperation(
            id="op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SYNC,
            status=OperationStatus.IN_PROGRESS
        )
        mock_operation_repo.get_by_id.return_value = operation
        
        result = await sync_coordinator.cancel_operation("op-1")
        
        assert result == False
        mock_operation_repo.update_status.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_endpoint_operations_success(self, sync_coordinator, mock_operation_repo):
        """Test successful endpoint operations retrieval."""
        expected_operations = [
            SyncOperation("op-1", "pool-1", "endpoint-1", OperationType.SYNC),
            SyncOperation("op-2", "pool-1", "endpoint-1", OperationType.SET_LATEST)
        ]
        mock_operation_repo.list_by_endpoint.return_value = expected_operations
        
        result = await sync_coordinator.get_endpoint_operations("endpoint-1", limit=5)
        
        assert result == expected_operations
        mock_operation_repo.list_by_endpoint.assert_called_once_with("endpoint-1", 5)
    
    @pytest.mark.asyncio
    async def test_get_pool_operations_success(self, sync_coordinator, mock_operation_repo):
        """Test successful pool operations retrieval."""
        expected_operations = [
            SyncOperation("op-1", "pool-1", "endpoint-1", OperationType.SYNC),
            SyncOperation("op-2", "pool-1", "endpoint-2", OperationType.REVERT)
        ]
        mock_operation_repo.list_by_pool.return_value = expected_operations
        
        result = await sync_coordinator.get_pool_operations("pool-1", limit=10)
        
        assert result == expected_operations
        mock_operation_repo.list_by_pool.assert_called_once_with("pool-1", 10)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])