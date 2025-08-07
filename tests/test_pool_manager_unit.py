#!/usr/bin/env python3
"""
Unit tests for PackagePoolManager core service.

Tests pool management functionality including creation, modification,
deletion, endpoint assignment, and status tracking.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from server.core.pool_manager import PackagePoolManager, PoolStatusInfo
from shared.models import (
    PackagePool, Endpoint, SyncStatus, SyncPolicy, ConflictResolution
)
from server.database.orm import ValidationError, NotFoundError


class TestPoolStatusInfo:
    """Test PoolStatusInfo helper class."""
    
    def test_pool_status_info_creation(self):
        """Test creating PoolStatusInfo with endpoints."""
        pool = PackagePool(
            id="pool-1",
            name="Test Pool",
            description="Test pool"
        )
        
        endpoints = [
            Endpoint("ep-1", "Endpoint 1", "host1", sync_status=SyncStatus.IN_SYNC),
            Endpoint("ep-2", "Endpoint 2", "host2", sync_status=SyncStatus.AHEAD),
            Endpoint("ep-3", "Endpoint 3", "host3", sync_status=SyncStatus.BEHIND),
            Endpoint("ep-4", "Endpoint 4", "host4", sync_status=SyncStatus.OFFLINE)
        ]
        
        status_info = PoolStatusInfo(pool, endpoints)
        
        assert status_info.pool == pool
        assert status_info.endpoints == endpoints
        assert status_info.total_endpoints == 4
        assert status_info.in_sync_count == 1
        assert status_info.ahead_count == 1
        assert status_info.behind_count == 1
        assert status_info.offline_count == 1
    
    def test_sync_percentage_calculation(self):
        """Test sync percentage calculation."""
        pool = PackagePool("pool-1", "Test Pool", "Test")
        
        # All in sync
        endpoints = [
            Endpoint("ep-1", "Endpoint 1", "host1", sync_status=SyncStatus.IN_SYNC),
            Endpoint("ep-2", "Endpoint 2", "host2", sync_status=SyncStatus.IN_SYNC)
        ]
        status_info = PoolStatusInfo(pool, endpoints)
        assert status_info.sync_percentage == 100.0
        
        # Half in sync
        endpoints[1].sync_status = SyncStatus.BEHIND
        status_info = PoolStatusInfo(pool, endpoints)
        assert status_info.sync_percentage == 50.0
        
        # None in sync
        endpoints[0].sync_status = SyncStatus.AHEAD
        status_info = PoolStatusInfo(pool, endpoints)
        assert status_info.sync_percentage == 0.0
        
        # Empty pool
        status_info = PoolStatusInfo(pool, [])
        assert status_info.sync_percentage == 100.0
    
    def test_overall_status_determination(self):
        """Test overall status determination logic."""
        pool = PackagePool("pool-1", "Test Pool", "Test")
        
        # Empty pool
        status_info = PoolStatusInfo(pool, [])
        assert status_info.overall_status == "empty"
        
        # Fully synced
        endpoints = [
            Endpoint("ep-1", "Endpoint 1", "host1", sync_status=SyncStatus.IN_SYNC),
            Endpoint("ep-2", "Endpoint 2", "host2", sync_status=SyncStatus.IN_SYNC)
        ]
        status_info = PoolStatusInfo(pool, endpoints)
        assert status_info.overall_status == "fully_synced"
        
        # All offline
        for ep in endpoints:
            ep.sync_status = SyncStatus.OFFLINE
        status_info = PoolStatusInfo(pool, endpoints)
        assert status_info.overall_status == "all_offline"
        
        # Partially synced
        endpoints[0].sync_status = SyncStatus.IN_SYNC
        endpoints[1].sync_status = SyncStatus.BEHIND
        status_info = PoolStatusInfo(pool, endpoints)
        assert status_info.overall_status == "partially_synced"
        
        # Out of sync
        endpoints[0].sync_status = SyncStatus.AHEAD
        endpoints[1].sync_status = SyncStatus.BEHIND
        status_info = PoolStatusInfo(pool, endpoints)
        assert status_info.overall_status == "out_of_sync"
    
    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        pool = PackagePool(
            id="pool-1",
            name="Test Pool",
            description="Test pool",
            target_state_id="state-1",
            sync_policy=SyncPolicy(auto_sync=True)
        )
        
        endpoints = [
            Endpoint("ep-1", "Endpoint 1", "host1", sync_status=SyncStatus.IN_SYNC),
            Endpoint("ep-2", "Endpoint 2", "host2", sync_status=SyncStatus.BEHIND)
        ]
        
        status_info = PoolStatusInfo(pool, endpoints)
        result = status_info.to_dict()
        
        expected_keys = [
            "pool_id", "pool_name", "total_endpoints", "in_sync_count",
            "ahead_count", "behind_count", "offline_count", "sync_percentage",
            "overall_status", "has_target_state", "auto_sync_enabled"
        ]
        
        for key in expected_keys:
            assert key in result
        
        assert result["pool_id"] == "pool-1"
        assert result["pool_name"] == "Test Pool"
        assert result["total_endpoints"] == 2
        assert result["in_sync_count"] == 1
        assert result["behind_count"] == 1
        assert result["has_target_state"] == True
        assert result["auto_sync_enabled"] == True


class TestPackagePoolManager:
    """Test PackagePoolManager core service."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        return MagicMock()
    
    @pytest.fixture
    def mock_pool_repo(self):
        """Create mock pool repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_endpoint_repo(self):
        """Create mock endpoint repository."""
        return AsyncMock()
    
    @pytest.fixture
    def pool_manager(self, mock_db_manager, mock_pool_repo, mock_endpoint_repo):
        """Create PackagePoolManager with mocked dependencies."""
        manager = PackagePoolManager(mock_db_manager)
        manager.pool_repo = mock_pool_repo
        manager.endpoint_repo = mock_endpoint_repo
        return manager
    
    @pytest.mark.asyncio
    async def test_create_pool_success(self, pool_manager, mock_pool_repo):
        """Test successful pool creation."""
        # Setup mock
        expected_pool = PackagePool(
            id="generated-id",
            name="Test Pool",
            description="Test description"
        )
        mock_pool_repo.create.return_value = expected_pool
        
        # Execute
        result = await pool_manager.create_pool("Test Pool", "Test description")
        
        # Verify
        assert result == expected_pool
        mock_pool_repo.create.assert_called_once()
        
        # Check that the created pool has correct properties
        call_args = mock_pool_repo.create.call_args[0][0]
        assert call_args.name == "Test Pool"
        assert call_args.description == "Test description"
        assert isinstance(call_args.sync_policy, SyncPolicy)
    
    @pytest.mark.asyncio
    async def test_create_pool_with_custom_sync_policy(self, pool_manager, mock_pool_repo):
        """Test pool creation with custom sync policy."""
        custom_policy = SyncPolicy(
            auto_sync=True,
            exclude_packages=["pkg1"],
            conflict_resolution=ConflictResolution.NEWEST
        )
        
        expected_pool = PackagePool(
            id="generated-id",
            name="Test Pool",
            description="Test description",
            sync_policy=custom_policy
        )
        mock_pool_repo.create.return_value = expected_pool
        
        result = await pool_manager.create_pool(
            "Test Pool", "Test description", custom_policy
        )
        
        assert result == expected_pool
        call_args = mock_pool_repo.create.call_args[0][0]
        assert call_args.sync_policy == custom_policy
    
    @pytest.mark.asyncio
    async def test_create_pool_empty_name_validation(self, pool_manager):
        """Test that empty pool name raises ValidationError."""
        with pytest.raises(ValidationError, match="Pool name cannot be empty"):
            await pool_manager.create_pool("", "Description")
        
        with pytest.raises(ValidationError, match="Pool name cannot be empty"):
            await pool_manager.create_pool("   ", "Description")
    
    @pytest.mark.asyncio
    async def test_create_pool_repository_error(self, pool_manager, mock_pool_repo):
        """Test pool creation with repository error."""
        mock_pool_repo.create.side_effect = ValidationError("Duplicate name")
        
        with pytest.raises(ValidationError, match="Duplicate name"):
            await pool_manager.create_pool("Test Pool", "Description")
    
    @pytest.mark.asyncio
    async def test_get_pool_success(self, pool_manager, mock_pool_repo):
        """Test successful pool retrieval."""
        expected_pool = PackagePool("pool-1", "Test Pool", "Description")
        mock_pool_repo.get_by_id.return_value = expected_pool
        mock_pool_repo.get_endpoints.return_value = ["endpoint-1", "endpoint-2"]
        
        result = await pool_manager.get_pool("pool-1")
        
        assert result == expected_pool
        assert result.endpoints == ["endpoint-1", "endpoint-2"]
        mock_pool_repo.get_by_id.assert_called_once_with("pool-1")
        mock_pool_repo.get_endpoints.assert_called_once_with("pool-1")
    
    @pytest.mark.asyncio
    async def test_get_pool_not_found(self, pool_manager, mock_pool_repo):
        """Test pool retrieval when pool doesn't exist."""
        mock_pool_repo.get_by_id.return_value = None
        
        result = await pool_manager.get_pool("non-existent")
        
        assert result is None
        mock_pool_repo.get_endpoints.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_pool_empty_id(self, pool_manager):
        """Test pool retrieval with empty ID."""
        result = await pool_manager.get_pool("")
        assert result is None
        
        result = await pool_manager.get_pool(None)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_pool_by_name_success(self, pool_manager, mock_pool_repo):
        """Test successful pool retrieval by name."""
        expected_pool = PackagePool("pool-1", "Test Pool", "Description")
        mock_pool_repo.get_by_name.return_value = expected_pool
        mock_pool_repo.get_endpoints.return_value = ["endpoint-1"]
        
        result = await pool_manager.get_pool_by_name("Test Pool")
        
        assert result == expected_pool
        assert result.endpoints == ["endpoint-1"]
        mock_pool_repo.get_by_name.assert_called_once_with("Test Pool")
    
    @pytest.mark.asyncio
    async def test_list_pools_success(self, pool_manager, mock_pool_repo):
        """Test successful pool listing."""
        pools = [
            PackagePool("pool-1", "Pool 1", "Description 1"),
            PackagePool("pool-2", "Pool 2", "Description 2")
        ]
        mock_pool_repo.list_all.return_value = pools
        mock_pool_repo.get_endpoints.side_effect = [["ep-1"], ["ep-2", "ep-3"]]
        
        result = await pool_manager.list_pools()
        
        assert len(result) == 2
        assert result[0].endpoints == ["ep-1"]
        assert result[1].endpoints == ["ep-2", "ep-3"]
        assert mock_pool_repo.get_endpoints.call_count == 2
    
    @pytest.mark.asyncio
    async def test_update_pool_success(self, pool_manager, mock_pool_repo):
        """Test successful pool update."""
        updated_pool = PackagePool("pool-1", "Updated Pool", "Updated description")
        mock_pool_repo.update.return_value = updated_pool
        mock_pool_repo.get_endpoints.return_value = ["endpoint-1"]
        
        result = await pool_manager.update_pool(
            "pool-1", 
            name="Updated Pool",
            description="Updated description"
        )
        
        assert result == updated_pool
        assert result.endpoints == ["endpoint-1"]
        mock_pool_repo.update.assert_called_once_with(
            "pool-1", 
            name="Updated Pool",
            description="Updated description"
        )
    
    @pytest.mark.asyncio
    async def test_update_pool_not_found(self, pool_manager, mock_pool_repo):
        """Test pool update when pool doesn't exist."""
        mock_pool_repo.update.side_effect = NotFoundError("Pool not found")
        
        with pytest.raises(NotFoundError):
            await pool_manager.update_pool("non-existent", name="New Name")
    
    @pytest.mark.asyncio
    async def test_update_pool_empty_id(self, pool_manager):
        """Test pool update with empty ID."""
        with pytest.raises(ValidationError, match="Pool ID cannot be empty"):
            await pool_manager.update_pool("", name="New Name")
    
    @pytest.mark.asyncio
    async def test_delete_pool_success(self, pool_manager, mock_pool_repo, mock_endpoint_repo):
        """Test successful pool deletion."""
        # Setup mocks
        endpoints = [
            Endpoint("ep-1", "Endpoint 1", "host1"),
            Endpoint("ep-2", "Endpoint 2", "host2")
        ]
        mock_endpoint_repo.list_by_pool.return_value = endpoints
        mock_endpoint_repo.remove_from_pool.return_value = True
        mock_pool_repo.delete.return_value = True
        
        result = await pool_manager.delete_pool("pool-1")
        
        assert result == True
        mock_endpoint_repo.list_by_pool.assert_called_once_with("pool-1")
        assert mock_endpoint_repo.remove_from_pool.call_count == 2
        mock_pool_repo.delete.assert_called_once_with("pool-1")
    
    @pytest.mark.asyncio
    async def test_delete_pool_not_found(self, pool_manager, mock_pool_repo, mock_endpoint_repo):
        """Test pool deletion when pool doesn't exist."""
        mock_endpoint_repo.list_by_pool.return_value = []
        mock_pool_repo.delete.return_value = False
        
        result = await pool_manager.delete_pool("non-existent")
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_assign_endpoint_success(self, pool_manager, mock_pool_repo, mock_endpoint_repo):
        """Test successful endpoint assignment."""
        # Setup mocks
        pool = PackagePool("pool-1", "Test Pool", "Description")
        endpoint = Endpoint("ep-1", "Endpoint 1", "host1", pool_id=None)
        
        mock_pool_repo.get_by_id.return_value = pool
        mock_endpoint_repo.get_by_id.return_value = endpoint
        mock_endpoint_repo.assign_to_pool.return_value = True
        mock_endpoint_repo.update_status.return_value = True
        
        result = await pool_manager.assign_endpoint("pool-1", "ep-1")
        
        assert result == True
        mock_endpoint_repo.assign_to_pool.assert_called_once_with("ep-1", "pool-1")
        mock_endpoint_repo.update_status.assert_called_once_with("ep-1", SyncStatus.BEHIND)
    
    @pytest.mark.asyncio
    async def test_assign_endpoint_move_from_previous_pool(self, pool_manager, mock_pool_repo, mock_endpoint_repo):
        """Test endpoint assignment when moving from another pool."""
        pool = PackagePool("pool-1", "Test Pool", "Description")
        endpoint = Endpoint("ep-1", "Endpoint 1", "host1", pool_id="old-pool")
        
        mock_pool_repo.get_by_id.return_value = pool
        mock_endpoint_repo.get_by_id.return_value = endpoint
        mock_endpoint_repo.remove_from_pool.return_value = True
        mock_endpoint_repo.assign_to_pool.return_value = True
        mock_endpoint_repo.update_status.return_value = True
        
        result = await pool_manager.assign_endpoint("pool-1", "ep-1")
        
        assert result == True
        mock_endpoint_repo.remove_from_pool.assert_called_once_with("ep-1")
        mock_endpoint_repo.assign_to_pool.assert_called_once_with("ep-1", "pool-1")
    
    @pytest.mark.asyncio
    async def test_assign_endpoint_pool_not_found(self, pool_manager, mock_pool_repo):
        """Test endpoint assignment when pool doesn't exist."""
        mock_pool_repo.get_by_id.return_value = None
        
        result = await pool_manager.assign_endpoint("non-existent", "ep-1")
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_assign_endpoint_endpoint_not_found(self, pool_manager, mock_pool_repo, mock_endpoint_repo):
        """Test endpoint assignment when endpoint doesn't exist."""
        pool = PackagePool("pool-1", "Test Pool", "Description")
        mock_pool_repo.get_by_id.return_value = pool
        mock_endpoint_repo.get_by_id.return_value = None
        
        result = await pool_manager.assign_endpoint("pool-1", "non-existent")
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_assign_endpoint_empty_ids(self, pool_manager):
        """Test endpoint assignment with empty IDs."""
        result = await pool_manager.assign_endpoint("", "ep-1")
        assert result == False
        
        result = await pool_manager.assign_endpoint("pool-1", "")
        assert result == False
    
    @pytest.mark.asyncio
    async def test_remove_endpoint_success(self, pool_manager, mock_endpoint_repo):
        """Test successful endpoint removal."""
        endpoint = Endpoint("ep-1", "Endpoint 1", "host1", pool_id="pool-1")
        mock_endpoint_repo.get_by_id.return_value = endpoint
        mock_endpoint_repo.remove_from_pool.return_value = True
        mock_endpoint_repo.update_status.return_value = True
        
        result = await pool_manager.remove_endpoint("pool-1", "ep-1")
        
        assert result == True
        mock_endpoint_repo.remove_from_pool.assert_called_once_with("ep-1")
        mock_endpoint_repo.update_status.assert_called_once_with("ep-1", SyncStatus.OFFLINE)
    
    @pytest.mark.asyncio
    async def test_remove_endpoint_wrong_pool(self, pool_manager, mock_endpoint_repo):
        """Test endpoint removal when endpoint is in different pool."""
        endpoint = Endpoint("ep-1", "Endpoint 1", "host1", pool_id="other-pool")
        mock_endpoint_repo.get_by_id.return_value = endpoint
        
        result = await pool_manager.remove_endpoint("pool-1", "ep-1")
        
        assert result == False
        mock_endpoint_repo.remove_from_pool.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_remove_endpoint_not_found(self, pool_manager, mock_endpoint_repo):
        """Test endpoint removal when endpoint doesn't exist."""
        mock_endpoint_repo.get_by_id.return_value = None
        
        result = await pool_manager.remove_endpoint("pool-1", "non-existent")
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_get_pool_status_success(self, pool_manager, mock_pool_repo, mock_endpoint_repo):
        """Test successful pool status retrieval."""
        pool = PackagePool("pool-1", "Test Pool", "Description")
        endpoints = [
            Endpoint("ep-1", "Endpoint 1", "host1", sync_status=SyncStatus.IN_SYNC)
        ]
        
        # Mock the get_pool method
        with patch.object(pool_manager, 'get_pool', return_value=pool):
            mock_endpoint_repo.list_by_pool.return_value = endpoints
            
            result = await pool_manager.get_pool_status("pool-1")
            
            assert isinstance(result, PoolStatusInfo)
            assert result.pool == pool
            assert result.endpoints == endpoints
    
    @pytest.mark.asyncio
    async def test_get_pool_status_pool_not_found(self, pool_manager):
        """Test pool status retrieval when pool doesn't exist."""
        with patch.object(pool_manager, 'get_pool', return_value=None):
            result = await pool_manager.get_pool_status("non-existent")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_set_target_state_success(self, pool_manager, mock_pool_repo, mock_endpoint_repo):
        """Test successful target state setting."""
        endpoints = [
            Endpoint("ep-1", "Endpoint 1", "host1", sync_status=SyncStatus.IN_SYNC),
            Endpoint("ep-2", "Endpoint 2", "host2", sync_status=SyncStatus.AHEAD)
        ]
        
        with patch.object(pool_manager, 'update_pool') as mock_update:
            mock_endpoint_repo.list_by_pool.return_value = endpoints
            mock_endpoint_repo.update_status.return_value = True
            
            result = await pool_manager.set_target_state("pool-1", "state-1")
            
            assert result == True
            mock_update.assert_called_once_with("pool-1", target_state_id="state-1")
            # Should update non-offline endpoints to BEHIND
            assert mock_endpoint_repo.update_status.call_count == 2
    
    @pytest.mark.asyncio
    async def test_clear_target_state_success(self, pool_manager):
        """Test successful target state clearing."""
        with patch.object(pool_manager, 'update_pool') as mock_update:
            result = await pool_manager.clear_target_state("pool-1")
            
            assert result == True
            mock_update.assert_called_once_with("pool-1", target_state_id=None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])