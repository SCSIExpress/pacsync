#!/usr/bin/env python3
"""
Full client-server communication integration tests.

This module tests complete client-server communication flows including:
- Client authentication and registration
- Pool management through client API
- Synchronization operations end-to-end
- Real-time status updates
- Error handling and recovery

Requirements: All requirements - integration validation
"""

import pytest
import asyncio
import json
import tempfile
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.api.main import create_app
from server.database.connection import DatabaseManager
from server.core.pool_manager import PackagePoolManager
from server.core.sync_coordinator import SyncCoordinator
from shared.models import (
    PackagePool, Endpoint, SyncStatus, PackageState, SystemState,
    SyncOperation, OperationType, OperationStatus
)


@pytest.fixture
async def test_server():
    """Create test server with in-memory database."""
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    # Set environment for test database
    os.environ['DATABASE_TYPE'] = 'internal'
    os.environ['DATABASE_URL'] = f'sqlite:///{temp_db.name}'
    
    app = create_app()
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # Create test data
    pool_manager = PackagePoolManager(db_manager)
    sync_coordinator = SyncCoordinator(db_manager)
    
    # Store in app state
    app.state.db_manager = db_manager
    app.state.pool_manager = pool_manager
    app.state.sync_coordinator = sync_coordinator
    
    yield app
    
    # Cleanup
    await db_manager.close()
    os.unlink(temp_db.name)


@pytest.fixture
def mock_client_config():
    """Mock client configuration."""
    config = Mock()
    config.get_server_url.return_value = "http://localhost:8080"
    config.get_server_timeout.return_value = 30
    config.get_retry_attempts.return_value = 3
    config.get_retry_delay.return_value = 1.0
    config.get_endpoint_name.return_value = "test_endpoint"
    config.get_pool_id.return_value = "test_pool"
    return config


@pytest.fixture
def sample_packages():
    """Sample package data for testing."""
    return [
        PackageState(
            package_name="package1",
            version="1.0.0",
            repository="core",
            installed_size=1024,
            dependencies=["dep1"]
        ),
        PackageState(
            package_name="package2", 
            version="2.0.0",
            repository="extra",
            installed_size=2048,
            dependencies=["dep2", "dep3"]
        ),
        PackageState(
            package_name="package3",
            version="3.0.0", 
            repository="community",
            installed_size=4096,
            dependencies=[]
        )
    ]


class TestClientServerAuthentication:
    """Test client authentication and registration with server."""
    
    @pytest.mark.asyncio
    async def test_client_registration_flow(self, test_server, mock_client_config):
        """Test complete client registration flow."""
        from fastapi.testclient import TestClient
        from client.api_client import PacmanSyncAPIClient
        
        with TestClient(test_server) as client:
            # Create API client
            api_client = PacmanSyncPacmanSyncAPIClient(mock_client_config)
            
            # Mock HTTP requests to test client
            with patch('aiohttp.ClientSession.post') as mock_post:
                # Mock successful registration response
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = {
                    "endpoint_id": "test-endpoint-123",
                    "token": "test-jwt-token",
                    "pool_id": "test_pool",
                    "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
                }
                mock_post.return_value.__aenter__.return_value = mock_response
                
                # Test registration
                result = await api_client.register_endpoint()
                
                assert result is True
                assert api_client._endpoint_id == "test-endpoint-123"
                assert api_client._auth_token == "test-jwt-token"
                
                # Verify registration request
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert "/api/endpoints" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_authentication_token_refresh(self, test_server, mock_client_config):
        """Test automatic token refresh."""
        from client.api_client import PacmanSyncAPIClient
        
        api_client = PacmanSyncPacmanSyncAPIClient(mock_client_config)
        api_client._endpoint_id = "test-endpoint-123"
        api_client._auth_token = "expired-token"
        api_client._token_expires_at = datetime.now() - timedelta(minutes=1)  # Expired
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock token refresh response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "token": "new-jwt-token",
                "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test token refresh
            result = await api_client._ensure_authenticated()
            
            assert result is True
            assert api_client._auth_token == "new-jwt-token"
    
    @pytest.mark.asyncio
    async def test_authentication_failure_handling(self, test_server, mock_client_config):
        """Test handling of authentication failures."""
        from client.api_client import PacmanSyncAPIClient
        
        api_client = PacmanSyncPacmanSyncAPIClient(mock_client_config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock authentication failure
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_response.json.return_value = {
                "error": {
                    "code": "AUTHENTICATION_FAILED",
                    "message": "Invalid credentials"
                }
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test authentication failure
            result = await api_client.register_endpoint()
            
            assert result is False
            assert api_client._endpoint_id is None
            assert api_client._auth_token is None


class TestPoolManagementIntegration:
    """Test pool management through client-server integration."""
    
    @pytest.mark.asyncio
    async def test_pool_creation_through_client(self, test_server, mock_client_config):
        """Test pool creation through client API."""
        from fastapi.testclient import TestClient
        from client.api_client import PacmanSyncAPIClient
        
        with TestClient(test_server) as client:
            api_client = PacmanSyncPacmanSyncAPIClient(mock_client_config)
            
            # Mock authenticated client
            api_client._endpoint_id = "test-endpoint-123"
            api_client._auth_token = "valid-token"
            api_client._token_expires_at = datetime.now() + timedelta(hours=1)
            
            with patch('aiohttp.ClientSession.post') as mock_post:
                # Mock pool creation response
                mock_response = AsyncMock()
                mock_response.status = 201
                mock_response.json.return_value = {
                    "id": "new-pool-123",
                    "name": "Test Pool",
                    "description": "Test pool description",
                    "endpoints": [],
                    "created_at": datetime.now().isoformat()
                }
                mock_post.return_value.__aenter__.return_value = mock_response
                
                # Test pool creation
                pool_data = {
                    "name": "Test Pool",
                    "description": "Test pool description"
                }
                result = await api_client.create_pool(pool_data)
                
                assert result is not None
                assert result["id"] == "new-pool-123"
                assert result["name"] == "Test Pool"
    
    @pytest.mark.asyncio
    async def test_endpoint_assignment_to_pool(self, test_server, mock_client_config):
        """Test endpoint assignment to pool through client."""
        from client.api_client import PacmanSyncAPIClient
        
        api_client = PacmanSyncAPIClient(mock_client_config)
        api_client._endpoint_id = "test-endpoint-123"
        api_client._auth_token = "valid-token"
        api_client._token_expires_at = datetime.now() + timedelta(hours=1)
        
        with patch('aiohttp.ClientSession.put') as mock_put:
            # Mock endpoint assignment response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "id": "test-endpoint-123",
                "name": "test_endpoint",
                "pool_id": "target-pool-123",
                "sync_status": "behind"
            }
            mock_put.return_value.__aenter__.return_value = mock_response
            
            # Test endpoint assignment
            result = await api_client.assign_to_pool("target-pool-123")
            
            assert result is True
            
            # Verify assignment request
            mock_put.assert_called_once()
            call_args = mock_put.call_args
            assert "test-endpoint-123" in str(call_args)


class TestSynchronizationIntegration:
    """Test end-to-end synchronization operations."""
    
    @pytest.mark.asyncio
    async def test_sync_to_latest_end_to_end(self, test_server, mock_client_config, sample_packages):
        """Test complete sync-to-latest operation."""
        from client.api_client import PacmanSyncAPIClient
        from client.sync_manager import SyncManager
        
        # Create authenticated API client
        api_client = PacmanSyncAPIClient(mock_client_config)
        api_client._endpoint_id = "test-endpoint-123"
        api_client._auth_token = "valid-token"
        api_client._token_expires_at = datetime.now() + timedelta(hours=1)
        
        # Mock sync manager components
        with patch('client.sync_manager.PacmanInterface') as mock_pacman_class:
            with patch('client.sync_manager.PackageSynchronizer') as mock_sync_class:
                with patch('client.sync_manager.StateManager') as mock_state_class:
                    
                    # Setup mocks
                    mock_pacman = Mock()
                    mock_pacman_class.return_value = mock_pacman
                    
                    mock_synchronizer = Mock()
                    mock_sync_class.return_value = mock_synchronizer
                    
                    mock_state_manager = Mock()
                    mock_state_class.return_value = mock_state_manager
                    
                    # Create sync manager
                    sync_manager = SyncManager(mock_client_config)
                    sync_manager._api_client = api_client
                    sync_manager._is_authenticated = True
                    sync_manager._endpoint_id = "test-endpoint-123"
                    
                    # Mock API responses for sync operation
                    with patch('aiohttp.ClientSession.post') as mock_post:
                        # Mock sync operation initiation
                        mock_response = AsyncMock()
                        mock_response.status = 202
                        mock_response.json.return_value = {
                            "operation_id": "sync-op-123",
                            "status": "pending",
                            "message": "Sync operation initiated"
                        }
                        mock_post.return_value.__aenter__.return_value = mock_response
                        
                        # Test sync operation
                        target_state = SystemState(
                            endpoint_id="test-endpoint-123",
                            timestamp=datetime.now(),
                            packages=sample_packages,
                            pacman_version="6.0.1",
                            architecture="x86_64"
                        )
                        
                        sync_manager.sync_to_latest(target_state)
                        
                        # Verify sync was initiated
                        mock_post.assert_called()
                        
                        # Simulate successful sync completion
                        sync_manager._handle_sync_completion("sync-op-123", True, "Sync completed successfully")
                        
                        # Verify state was updated
                        mock_state_manager.save_state.assert_called()
    
    @pytest.mark.asyncio
    async def test_set_as_latest_operation(self, test_server, mock_client_config, sample_packages):
        """Test set-as-latest operation end-to-end."""
        from client.api_client import PacmanSyncAPIClient
        from client.sync_manager import SyncManager
        
        api_client = PacmanSyncAPIClient(mock_client_config)
        api_client._endpoint_id = "test-endpoint-123"
        api_client._auth_token = "valid-token"
        api_client._token_expires_at = datetime.now() + timedelta(hours=1)
        
        with patch('client.sync_manager.PacmanInterface') as mock_pacman_class:
            with patch('client.sync_manager.PackageSynchronizer') as mock_sync_class:
                with patch('client.sync_manager.StateManager') as mock_state_class:
                    
                    # Setup mocks
                    mock_pacman = Mock()
                    mock_pacman_class.return_value = mock_pacman
                    
                    # Mock current system state
                    current_state = SystemState(
                        endpoint_id="test-endpoint-123",
                        timestamp=datetime.now(),
                        packages=sample_packages,
                        pacman_version="6.0.1",
                        architecture="x86_64"
                    )
                    mock_pacman.get_system_state.return_value = current_state
                    
                    sync_manager = SyncManager(mock_client_config)
                    sync_manager._api_client = api_client
                    sync_manager._is_authenticated = True
                    sync_manager._endpoint_id = "test-endpoint-123"
                    
                    # Mock API response for set-latest operation
                    with patch('aiohttp.ClientSession.post') as mock_post:
                        mock_response = AsyncMock()
                        mock_response.status = 200
                        mock_response.json.return_value = {
                            "operation_id": "set-latest-op-123",
                            "status": "completed",
                            "message": "State set as latest for pool"
                        }
                        mock_post.return_value.__aenter__.return_value = mock_response
                        
                        # Test set-as-latest operation
                        sync_manager.set_as_latest()
                        
                        # Verify current state was captured
                        mock_pacman.get_system_state.assert_called_with("test-endpoint-123")
                        
                        # Verify API call was made
                        mock_post.assert_called()
    
    @pytest.mark.asyncio
    async def test_revert_operation_with_rollback(self, test_server, mock_client_config, sample_packages):
        """Test revert operation with state rollback."""
        from client.api_client import PacmanSyncAPIClient
        from client.sync_manager import SyncManager
        
        api_client = PacmanSyncAPIClient(mock_client_config)
        api_client._endpoint_id = "test-endpoint-123"
        api_client._auth_token = "valid-token"
        api_client._token_expires_at = datetime.now() + timedelta(hours=1)
        
        with patch('client.sync_manager.PacmanInterface') as mock_pacman_class:
            with patch('client.sync_manager.PackageSynchronizer') as mock_sync_class:
                with patch('client.sync_manager.StateManager') as mock_state_class:
                    
                    # Setup mocks
                    mock_state_manager = Mock()
                    mock_state_class.return_value = mock_state_manager
                    
                    # Mock previous state
                    previous_state = SystemState(
                        endpoint_id="test-endpoint-123",
                        timestamp=datetime.now() - timedelta(hours=1),
                        packages=sample_packages[:-1],  # Different package set
                        pacman_version="6.0.1",
                        architecture="x86_64"
                    )
                    mock_state_manager.get_previous_state.return_value = previous_state
                    
                    sync_manager = SyncManager(mock_client_config)
                    sync_manager._api_client = api_client
                    sync_manager._is_authenticated = True
                    sync_manager._endpoint_id = "test-endpoint-123"
                    
                    # Mock API response for revert operation
                    with patch('aiohttp.ClientSession.post') as mock_post:
                        mock_response = AsyncMock()
                        mock_response.status = 202
                        mock_response.json.return_value = {
                            "operation_id": "revert-op-123",
                            "status": "pending",
                            "message": "Revert operation initiated"
                        }
                        mock_post.return_value.__aenter__.return_value = mock_response
                        
                        # Test revert operation
                        sync_manager.revert_to_previous()
                        
                        # Verify previous state was retrieved
                        mock_state_manager.get_previous_state.assert_called()
                        
                        # Verify API call was made
                        mock_post.assert_called()


class TestRealTimeStatusUpdates:
    """Test real-time status updates between client and server."""
    
    @pytest.mark.asyncio
    async def test_status_polling_integration(self, test_server, mock_client_config):
        """Test periodic status polling from client to server."""
        from client.api_client import PacmanSyncAPIClient
        from client.sync_manager import SyncManager
        
        api_client = PacmanSyncAPIClient(mock_client_config)
        api_client._endpoint_id = "test-endpoint-123"
        api_client._auth_token = "valid-token"
        api_client._token_expires_at = datetime.now() + timedelta(hours=1)
        
        with patch('client.sync_manager.PacmanInterface'):
            with patch('client.sync_manager.PackageSynchronizer'):
                with patch('client.sync_manager.StateManager'):
                    
                    sync_manager = SyncManager(mock_client_config)
                    sync_manager._api_client = api_client
                    sync_manager._is_authenticated = True
                    sync_manager._endpoint_id = "test-endpoint-123"
                    
                    # Mock status polling responses
                    with patch('aiohttp.ClientSession.get') as mock_get:
                        status_responses = [
                            {"status": "behind", "last_sync": None, "pending_operations": []},
                            {"status": "syncing", "last_sync": None, "pending_operations": ["sync-op-123"]},
                            {"status": "in_sync", "last_sync": datetime.now().isoformat(), "pending_operations": []}
                        ]
                        
                        mock_responses = []
                        for response_data in status_responses:
                            mock_response = AsyncMock()
                            mock_response.status = 200
                            mock_response.json.return_value = response_data
                            mock_responses.append(mock_response)
                        
                        mock_get.return_value.__aenter__.side_effect = mock_responses
                        
                        # Track status changes
                        status_changes = []
                        sync_manager.status_changed.connect(lambda status: status_changes.append(status))
                        
                        # Simulate multiple status polls
                        for _ in range(3):
                            await sync_manager._poll_server_status()
                        
                        # Verify status progression
                        assert len(status_changes) >= 2  # Should have changed at least twice
                        assert mock_get.call_count == 3
    
    @pytest.mark.asyncio
    async def test_operation_progress_tracking(self, test_server, mock_client_config):
        """Test tracking operation progress through status updates."""
        from client.api_client import PacmanSyncAPIClient
        
        api_client = PacmanSyncAPIClient(mock_client_config)
        api_client._endpoint_id = "test-endpoint-123"
        api_client._auth_token = "valid-token"
        api_client._token_expires_at = datetime.now() + timedelta(hours=1)
        
        # Mock operation progress responses
        with patch('aiohttp.ClientSession.get') as mock_get:
            progress_responses = [
                {
                    "operation_id": "sync-op-123",
                    "status": "in_progress",
                    "progress": 25,
                    "current_stage": "analyzing",
                    "message": "Analyzing package differences"
                },
                {
                    "operation_id": "sync-op-123", 
                    "status": "in_progress",
                    "progress": 75,
                    "current_stage": "installing",
                    "message": "Installing packages"
                },
                {
                    "operation_id": "sync-op-123",
                    "status": "completed",
                    "progress": 100,
                    "current_stage": "completed",
                    "message": "Sync completed successfully"
                }
            ]
            
            mock_responses = []
            for response_data in progress_responses:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = response_data
                mock_responses.append(mock_response)
            
            mock_get.return_value.__aenter__.side_effect = mock_responses
            
            # Test operation progress tracking
            progress_updates = []
            
            for expected_response in progress_responses:
                result = await api_client.get_operation_status("sync-op-123")
                progress_updates.append(result)
            
            # Verify progress tracking
            assert len(progress_updates) == 3
            assert progress_updates[0]["progress"] == 25
            assert progress_updates[1]["progress"] == 75
            assert progress_updates[2]["status"] == "completed"


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_network_failure_recovery(self, test_server, mock_client_config):
        """Test recovery from network failures."""
        from client.api_client import PacmanSyncAPIClient
        from client.sync_manager import SyncManager
        import aiohttp
        
        api_client = PacmanSyncAPIClient(mock_client_config)
        api_client._endpoint_id = "test-endpoint-123"
        api_client._auth_token = "valid-token"
        api_client._token_expires_at = datetime.now() + timedelta(hours=1)
        
        with patch('client.sync_manager.PacmanInterface'):
            with patch('client.sync_manager.PackageSynchronizer'):
                with patch('client.sync_manager.StateManager'):
                    
                    sync_manager = SyncManager(mock_client_config)
                    sync_manager._api_client = api_client
                    sync_manager._is_authenticated = True
                    sync_manager._endpoint_id = "test-endpoint-123"
                    
                    # Mock network failure followed by recovery
                    with patch('aiohttp.ClientSession.get') as mock_get:
                        # First call fails with network error
                        mock_get.side_effect = [
                            aiohttp.ClientError("Network unreachable"),
                            aiohttp.ClientError("Connection timeout"),
                            # Third call succeeds
                            AsyncMock(status=200, json=AsyncMock(return_value={
                                "status": "in_sync",
                                "last_sync": datetime.now().isoformat(),
                                "pending_operations": []
                            }))
                        ]
                        
                        # Track error and recovery
                        errors = []
                        sync_manager.error_occurred.connect(lambda msg: errors.append(msg))
                        
                        # Attempt status polling with retries
                        for attempt in range(3):
                            try:
                                await sync_manager._poll_server_status()
                                break  # Success on third attempt
                            except Exception:
                                continue
                        
                        # Verify retry behavior
                        assert mock_get.call_count == 3
                        assert len(errors) >= 2  # Should have logged network errors
    
    @pytest.mark.asyncio
    async def test_server_error_handling(self, test_server, mock_client_config):
        """Test handling of server errors."""
        from client.api_client import PacmanSyncAPIClient
        
        api_client = PacmanSyncAPIClient(mock_client_config)
        api_client._endpoint_id = "test-endpoint-123"
        api_client._auth_token = "valid-token"
        api_client._token_expires_at = datetime.now() + timedelta(hours=1)
        
        # Mock server error responses
        with patch('aiohttp.ClientSession.post') as mock_post:
            error_responses = [
                (500, {"error": {"code": "INTERNAL_ERROR", "message": "Database connection failed"}}),
                (409, {"error": {"code": "OPERATION_CONFLICT", "message": "Another operation is in progress"}}),
                (422, {"error": {"code": "VALIDATION_ERROR", "message": "Invalid package state data"}})
            ]
            
            for status_code, error_data in error_responses:
                mock_response = AsyncMock()
                mock_response.status = status_code
                mock_response.json.return_value = error_data
                mock_post.return_value.__aenter__.return_value = mock_response
                
                # Test error handling
                result = await api_client.initiate_sync()
                
                assert result is False or result is None
                
                # Verify error was handled gracefully
                mock_post.assert_called()
                mock_post.reset_mock()
    
    @pytest.mark.asyncio
    async def test_authentication_expiry_handling(self, test_server, mock_client_config):
        """Test handling of authentication token expiry."""
        from client.api_client import PacmanSyncAPIClient
        
        api_client = PacmanSyncAPIClient(mock_client_config)
        api_client._endpoint_id = "test-endpoint-123"
        api_client._auth_token = "expired-token"
        api_client._token_expires_at = datetime.now() - timedelta(minutes=1)  # Expired
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock token refresh success
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "token": "new-valid-token",
                "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test automatic token refresh
            result = await api_client._ensure_authenticated()
            
            assert result is True
            assert api_client._auth_token == "new-valid-token"
            assert api_client._token_expires_at > datetime.now()


def run_integration_tests():
    """Run all client-server integration tests."""
    print("=" * 60)
    print("CLIENT-SERVER INTEGRATION TESTS")
    print("=" * 60)
    
    # Run pytest with this file
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)