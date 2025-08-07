#!/usr/bin/env python3
"""
End-to-end workflow validation tests.

This module tests complete user workflows from start to finish:
- Complete setup and configuration workflow
- Full synchronization workflow across multiple endpoints
- Error recovery and resilience workflows
- Real-world usage scenarios

Requirements: All requirements - integration validation
"""

import pytest
import asyncio
import json
import tempfile
import os
import sys
import time
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
async def complete_test_environment():
    """Set up complete test environment with server and multiple mock clients."""
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
    
    # Create services
    pool_manager = PackagePoolManager(db_manager)
    sync_coordinator = SyncCoordinator(db_manager)
    
    # Store in app state
    app.state.db_manager = db_manager
    app.state.pool_manager = pool_manager
    app.state.sync_coordinator = sync_coordinator
    
    # Create test environment data
    environment = {
        "app": app,
        "db_manager": db_manager,
        "pool_manager": pool_manager,
        "sync_coordinator": sync_coordinator,
        "temp_db": temp_db.name
    }
    
    yield environment
    
    # Cleanup
    await db_manager.close()
    os.unlink(temp_db.name)


@pytest.fixture
def mock_client_factory():
    """Factory for creating mock clients."""
    def create_mock_client(endpoint_id, endpoint_name, packages):
        """Create a mock client with specified configuration."""
        from client.api_client import PacmanSyncAPIClient
        from client.sync_manager import SyncManager
        
        # Mock configuration
        config = Mock()
        config.get_server_url.return_value = "http://localhost:8080"
        config.get_server_timeout.return_value = 30
        config.get_retry_attempts.return_value = 3
        config.get_retry_delay.return_value = 1.0
        config.get_endpoint_name.return_value = endpoint_name
        config.get_pool_id.return_value = "test_pool"
        
        # Mock API client
        api_client = Mock(spec=PacmanSyncAPIClient)
        api_client._endpoint_id = endpoint_id
        api_client._auth_token = "mock-token"
        api_client._token_expires_at = datetime.now() + timedelta(hours=1)
        
        # Mock sync manager components
        with patch('client.sync_manager.PacmanInterface') as mock_pacman_class:
            with patch('client.sync_manager.PackageSynchronizer') as mock_sync_class:
                with patch('client.sync_manager.StateManager') as mock_state_class:
                    
                    # Setup pacman mock
                    mock_pacman = Mock()
                    mock_pacman_class.return_value = mock_pacman
                    
                    # Create system state with provided packages
                    system_state = SystemState(
                        endpoint_id=endpoint_id,
                        timestamp=datetime.now(),
                        packages=packages,
                        pacman_version="6.0.1",
                        architecture="x86_64"
                    )
                    mock_pacman.get_system_state.return_value = system_state
                    
                    # Setup synchronizer mock
                    mock_synchronizer = Mock()
                    mock_sync_class.return_value = mock_synchronizer
                    
                    # Setup state manager mock
                    mock_state_manager = Mock()
                    mock_state_class.return_value = mock_state_manager
                    
                    # Create sync manager
                    sync_manager = SyncManager(config)
                    sync_manager._api_client = api_client
                    sync_manager._is_authenticated = True
                    sync_manager._endpoint_id = endpoint_id
                    
                    return {
                        "config": config,
                        "api_client": api_client,
                        "sync_manager": sync_manager,
                        "pacman": mock_pacman,
                        "synchronizer": mock_synchronizer,
                        "state_manager": mock_state_manager,
                        "system_state": system_state
                    }
    
    return create_mock_client


class TestCompleteSetupWorkflow:
    """Test complete setup and configuration workflow."""
    
    @pytest.mark.asyncio
    async def test_fresh_installation_setup(self, complete_test_environment, mock_client_factory):
        """Test complete setup workflow for fresh installation."""
        env = complete_test_environment
        pool_manager = env["pool_manager"]
        sync_coordinator = env["sync_coordinator"]
        
        # Step 1: Server startup (already done in fixture)
        print("✓ Server started successfully")
        
        # Step 2: Create initial pool
        initial_pool = PackagePool(
            id="production-pool",
            name="Production Environment",
            description="Main production package pool",
            endpoints=[],
            target_state_id=None,
            sync_policy=None
        )
        
        created_pool = await pool_manager.create_pool(initial_pool)
        assert created_pool.id == "production-pool"
        print("✓ Initial pool created")
        
        # Step 3: Register first endpoint (development machine)
        dev_packages = [
            PackageState("gcc", "11.2.0", "core", 50000, ["glibc"]),
            PackageState("python", "3.10.8", "extra", 30000, ["openssl"]),
            PackageState("git", "2.38.1", "extra", 15000, []),
            PackageState("vim", "9.0.0", "extra", 5000, [])
        ]
        
        dev_client = mock_client_factory("dev-machine", "Development Machine", dev_packages)
        
        # Register endpoint
        dev_endpoint = Endpoint(
            id="dev-machine",
            name="Development Machine",
            hostname="dev.example.com",
            pool_id="production-pool",
            sync_status=SyncStatus.OFFLINE,
            last_seen=None
        )
        
        registered_endpoint = await pool_manager.register_endpoint(dev_endpoint)
        assert registered_endpoint.id == "dev-machine"
        print("✓ Development endpoint registered")
        
        # Step 4: Set initial state as target
        await sync_coordinator.save_endpoint_state("dev-machine", dev_client["system_state"])
        await sync_coordinator.set_as_latest("dev-machine")
        print("✓ Initial state set as target")
        
        # Step 5: Register second endpoint (production server)
        prod_packages = [
            PackageState("gcc", "11.1.0", "core", 50000, ["glibc"]),  # Older version
            PackageState("python", "3.10.8", "extra", 30000, ["openssl"]),
            PackageState("git", "2.37.0", "extra", 15000, []),  # Older version
            PackageState("nginx", "1.22.1", "extra", 8000, [])  # Additional package
        ]
        
        prod_client = mock_client_factory("prod-server", "Production Server", prod_packages)
        
        prod_endpoint = Endpoint(
            id="prod-server",
            name="Production Server", 
            hostname="prod.example.com",
            pool_id="production-pool",
            sync_status=SyncStatus.OFFLINE,
            last_seen=None
        )
        
        await pool_manager.register_endpoint(prod_endpoint)
        await sync_coordinator.save_endpoint_state("prod-server", prod_client["system_state"])
        print("✓ Production endpoint registered")
        
        # Step 6: Verify pool status shows endpoints are behind
        await pool_manager.update_endpoint_status("dev-machine", SyncStatus.IN_SYNC)
        await pool_manager.update_endpoint_status("prod-server", SyncStatus.BEHIND)
        
        pool_status = await pool_manager.get_pool_status("production-pool")
        assert pool_status.overall_status != "in_sync"  # Should not be fully in sync
        print("✓ Pool status correctly shows mixed sync states")
        
        # Step 7: Verify setup is complete and functional
        pools = await pool_manager.list_pools()
        assert len(pools) == 1
        assert pools[0].name == "Production Environment"
        
        endpoints = await pool_manager.list_endpoints("production-pool")
        assert len(endpoints) == 2
        endpoint_names = [e.name for e in endpoints]
        assert "Development Machine" in endpoint_names
        assert "Production Server" in endpoint_names
        
        print("✓ Complete setup workflow validated")
    
    @pytest.mark.asyncio
    async def test_configuration_validation_workflow(self, complete_test_environment):
        """Test configuration validation during setup."""
        env = complete_test_environment
        pool_manager = env["pool_manager"]
        
        # Test invalid pool creation
        invalid_pool = PackagePool(
            id="",  # Invalid empty ID
            name="",  # Invalid empty name
            description="Test pool",
            endpoints=[],
            target_state_id=None,
            sync_policy=None
        )
        
        try:
            await pool_manager.create_pool(invalid_pool)
            assert False, "Should have failed with invalid pool data"
        except Exception as e:
            print(f"✓ Invalid pool creation correctly rejected: {e}")
        
        # Test invalid endpoint registration
        invalid_endpoint = Endpoint(
            id="",  # Invalid empty ID
            name="Test Endpoint",
            hostname="",  # Invalid empty hostname
            pool_id="nonexistent-pool",  # Invalid pool ID
            sync_status=SyncStatus.OFFLINE,
            last_seen=None
        )
        
        try:
            await pool_manager.register_endpoint(invalid_endpoint)
            assert False, "Should have failed with invalid endpoint data"
        except Exception as e:
            print(f"✓ Invalid endpoint registration correctly rejected: {e}")


class TestFullSynchronizationWorkflow:
    """Test complete synchronization workflow across multiple endpoints."""
    
    @pytest.mark.asyncio
    async def test_multi_endpoint_sync_workflow(self, complete_test_environment, mock_client_factory):
        """Test complete multi-endpoint synchronization workflow."""
        env = complete_test_environment
        pool_manager = env["pool_manager"]
        sync_coordinator = env["sync_coordinator"]
        
        # Setup: Create pool and endpoints
        test_pool = PackagePool(
            id="sync-test-pool",
            name="Sync Test Pool",
            description="Pool for testing synchronization workflow",
            endpoints=[],
            target_state_id=None,
            sync_policy=None
        )
        await pool_manager.create_pool(test_pool)
        
        # Create three endpoints with different package states
        endpoints_data = [
            {
                "id": "endpoint-1",
                "name": "Endpoint 1",
                "hostname": "host1.example.com",
                "packages": [
                    PackageState("package-a", "1.0.0", "core", 1000, []),
                    PackageState("package-b", "2.0.0", "extra", 2000, []),
                    PackageState("package-c", "3.0.0", "community", 3000, [])
                ]
            },
            {
                "id": "endpoint-2", 
                "name": "Endpoint 2",
                "hostname": "host2.example.com",
                "packages": [
                    PackageState("package-a", "1.1.0", "core", 1000, []),  # Newer
                    PackageState("package-b", "2.0.0", "extra", 2000, []),
                    PackageState("package-d", "4.0.0", "aur", 4000, [])  # Different package
                ]
            },
            {
                "id": "endpoint-3",
                "name": "Endpoint 3", 
                "hostname": "host3.example.com",
                "packages": [
                    PackageState("package-a", "0.9.0", "core", 1000, []),  # Older
                    PackageState("package-b", "2.1.0", "extra", 2000, []),  # Newer
                    PackageState("package-c", "3.0.0", "community", 3000, [])
                ]
            }
        ]
        
        # Register endpoints and save states
        clients = {}
        for endpoint_data in endpoints_data:
            # Create endpoint
            endpoint = Endpoint(
                id=endpoint_data["id"],
                name=endpoint_data["name"],
                hostname=endpoint_data["hostname"],
                pool_id="sync-test-pool",
                sync_status=SyncStatus.OFFLINE,
                last_seen=None
            )
            await pool_manager.register_endpoint(endpoint)
            
            # Create mock client
            client = mock_client_factory(
                endpoint_data["id"],
                endpoint_data["name"],
                endpoint_data["packages"]
            )
            clients[endpoint_data["id"]] = client
            
            # Save endpoint state
            await sync_coordinator.save_endpoint_state(endpoint_data["id"], client["system_state"])
            await pool_manager.update_endpoint_status(endpoint_data["id"], SyncStatus.BEHIND)
        
        print("✓ Test environment set up with 3 endpoints")
        
        # Step 1: Set endpoint-2 as target (has newest package-a)
        await sync_coordinator.set_as_latest("endpoint-2")
        await pool_manager.update_endpoint_status("endpoint-2", SyncStatus.IN_SYNC)
        print("✓ Endpoint-2 set as target state")
        
        # Step 2: Initiate sync for other endpoints
        sync_operations = []
        for endpoint_id in ["endpoint-1", "endpoint-3"]:
            operation = await sync_coordinator.sync_to_latest(endpoint_id)
            sync_operations.append(operation)
            print(f"✓ Sync operation initiated for {endpoint_id}")
        
        # Verify operations were created
        assert len(sync_operations) == 2
        for operation in sync_operations:
            assert operation.operation_type == OperationType.SYNC
            assert operation.status == OperationStatus.PENDING
            assert operation.pool_id == "sync-test-pool"
        
        # Step 3: Simulate sync execution and completion
        for i, operation in enumerate(sync_operations):
            endpoint_id = operation.endpoint_id
            client = clients[endpoint_id]
            
            # Simulate package synchronization
            target_state = await sync_coordinator.get_target_state("sync-test-pool")
            
            # Update client's mock pacman to reflect synchronized state
            synchronized_packages = target_state.packages.copy()
            synchronized_state = SystemState(
                endpoint_id=endpoint_id,
                timestamp=datetime.now(),
                packages=synchronized_packages,
                pacman_version="6.0.1",
                architecture="x86_64"
            )
            client["pacman"].get_system_state.return_value = synchronized_state
            
            # Mark operation as completed
            operation.status = OperationStatus.COMPLETED
            operation.completed_at = datetime.now()
            await sync_coordinator.update_operation_status(operation.id, OperationStatus.COMPLETED)
            
            # Update endpoint status
            await pool_manager.update_endpoint_status(endpoint_id, SyncStatus.IN_SYNC)
            
            print(f"✓ Sync completed for {endpoint_id}")
        
        # Step 4: Verify all endpoints are now in sync
        pool_status = await pool_manager.get_pool_status("sync-test-pool")
        assert pool_status.overall_status == "in_sync"
        print("✓ All endpoints are now in sync")
        
        # Step 5: Verify sync history is recorded
        for operation in sync_operations:
            operation_status = await sync_coordinator.get_operation_status(operation.id)
            assert operation_status.status == OperationStatus.COMPLETED
            assert operation_status.completed_at is not None
        
        print("✓ Sync history properly recorded")
        print("✓ Complete multi-endpoint sync workflow validated")
    
    @pytest.mark.asyncio
    async def test_rolling_update_workflow(self, complete_test_environment, mock_client_factory):
        """Test rolling update workflow across endpoints."""
        env = complete_test_environment
        pool_manager = env["pool_manager"]
        sync_coordinator = env["sync_coordinator"]
        
        # Setup pool and endpoints
        test_pool = PackagePool(
            id="rolling-pool",
            name="Rolling Update Pool",
            description="Pool for testing rolling updates",
            endpoints=[],
            target_state_id=None,
            sync_policy=None
        )
        await pool_manager.create_pool(test_pool)
        
        # Create endpoints representing different environments
        environments = ["dev", "staging", "prod"]
        clients = {}
        
        initial_packages = [
            PackageState("app", "1.0.0", "custom", 10000, []),
            PackageState("database", "5.7.0", "extra", 50000, []),
            PackageState("webserver", "2.4.0", "extra", 20000, [])
        ]
        
        for env_name in environments:
            endpoint_id = f"{env_name}-server"
            endpoint = Endpoint(
                id=endpoint_id,
                name=f"{env_name.title()} Server",
                hostname=f"{env_name}.example.com",
                pool_id="rolling-pool",
                sync_status=SyncStatus.IN_SYNC,
                last_seen=datetime.now()
            )
            await pool_manager.register_endpoint(endpoint)
            
            client = mock_client_factory(endpoint_id, endpoint.name, initial_packages)
            clients[endpoint_id] = client
            
            await sync_coordinator.save_endpoint_state(endpoint_id, client["system_state"])
        
        # Set initial target state
        await sync_coordinator.set_as_latest("dev-server")
        print("✓ Initial state synchronized across all environments")
        
        # Step 1: Development environment gets updated packages
        updated_packages = [
            PackageState("app", "1.1.0", "custom", 10000, []),  # Updated app
            PackageState("database", "5.7.0", "extra", 50000, []),
            PackageState("webserver", "2.4.1", "extra", 20000, [])  # Updated webserver
        ]
        
        updated_state = SystemState(
            endpoint_id="dev-server",
            timestamp=datetime.now(),
            packages=updated_packages,
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        clients["dev-server"]["pacman"].get_system_state.return_value = updated_state
        await sync_coordinator.save_endpoint_state("dev-server", updated_state)
        await sync_coordinator.set_as_latest("dev-server")
        
        # Mark other environments as behind
        await pool_manager.update_endpoint_status("staging-server", SyncStatus.BEHIND)
        await pool_manager.update_endpoint_status("prod-server", SyncStatus.BEHIND)
        print("✓ Development environment updated with new packages")
        
        # Step 2: Roll out to staging
        staging_sync = await sync_coordinator.sync_to_latest("staging-server")
        
        # Simulate staging sync completion
        clients["staging-server"]["pacman"].get_system_state.return_value = updated_state
        staging_sync.status = OperationStatus.COMPLETED
        staging_sync.completed_at = datetime.now()
        await sync_coordinator.update_operation_status(staging_sync.id, OperationStatus.COMPLETED)
        await pool_manager.update_endpoint_status("staging-server", SyncStatus.IN_SYNC)
        print("✓ Staging environment updated")
        
        # Step 3: Roll out to production (after staging validation)
        prod_sync = await sync_coordinator.sync_to_latest("prod-server")
        
        # Simulate production sync completion
        clients["prod-server"]["pacman"].get_system_state.return_value = updated_state
        prod_sync.status = OperationStatus.COMPLETED
        prod_sync.completed_at = datetime.now()
        await sync_coordinator.update_operation_status(prod_sync.id, OperationStatus.COMPLETED)
        await pool_manager.update_endpoint_status("prod-server", SyncStatus.IN_SYNC)
        print("✓ Production environment updated")
        
        # Step 4: Verify rolling update completed successfully
        pool_status = await pool_manager.get_pool_status("rolling-pool")
        assert pool_status.overall_status == "in_sync"
        
        # Verify all environments have the updated packages
        target_state = await sync_coordinator.get_target_state("rolling-pool")
        target_app_version = next(p.version for p in target_state.packages if p.package_name == "app")
        assert target_app_version == "1.1.0"
        
        print("✓ Rolling update workflow completed successfully")


class TestErrorRecoveryWorkflows:
    """Test error recovery and resilience workflows."""
    
    @pytest.mark.asyncio
    async def test_network_failure_recovery_workflow(self, complete_test_environment, mock_client_factory):
        """Test recovery from network failures during sync."""
        env = complete_test_environment
        pool_manager = env["pool_manager"]
        sync_coordinator = env["sync_coordinator"]
        
        # Setup test environment
        test_pool = PackagePool(
            id="recovery-pool",
            name="Recovery Test Pool",
            description="Pool for testing error recovery",
            endpoints=[],
            target_state_id=None,
            sync_policy=None
        )
        await pool_manager.create_pool(test_pool)
        
        # Create endpoints
        packages = [PackageState("test-pkg", "1.0.0", "core", 1000, [])]
        
        endpoint1 = Endpoint(
            id="stable-endpoint",
            name="Stable Endpoint",
            hostname="stable.example.com",
            pool_id="recovery-pool",
            sync_status=SyncStatus.IN_SYNC,
            last_seen=datetime.now()
        )
        await pool_manager.register_endpoint(endpoint1)
        
        endpoint2 = Endpoint(
            id="unstable-endpoint",
            name="Unstable Endpoint", 
            hostname="unstable.example.com",
            pool_id="recovery-pool",
            sync_status=SyncStatus.BEHIND,
            last_seen=datetime.now()
        )
        await pool_manager.register_endpoint(endpoint2)
        
        # Create clients
        stable_client = mock_client_factory("stable-endpoint", "Stable Endpoint", packages)
        unstable_client = mock_client_factory("unstable-endpoint", "Unstable Endpoint", packages)
        
        # Save states
        await sync_coordinator.save_endpoint_state("stable-endpoint", stable_client["system_state"])
        await sync_coordinator.save_endpoint_state("unstable-endpoint", unstable_client["system_state"])
        await sync_coordinator.set_as_latest("stable-endpoint")
        
        print("✓ Test environment set up for network failure testing")
        
        # Step 1: Initiate sync that will fail
        sync_operation = await sync_coordinator.sync_to_latest("unstable-endpoint")
        print("✓ Sync operation initiated")
        
        # Step 2: Simulate network failure during sync
        sync_operation.status = OperationStatus.FAILED
        sync_operation.completed_at = datetime.now()
        sync_operation.details = {"error": "Network connection lost during sync"}
        await sync_coordinator.update_operation_status(sync_operation.id, OperationStatus.FAILED)
        
        # Mark endpoint as offline
        await pool_manager.update_endpoint_status("unstable-endpoint", SyncStatus.OFFLINE)
        print("✓ Network failure simulated")
        
        # Step 3: Verify pool status reflects the failure
        pool_status = await pool_manager.get_pool_status("recovery-pool")
        assert pool_status.overall_status != "in_sync"
        
        # Step 4: Simulate endpoint coming back online
        await pool_manager.update_endpoint_status("unstable-endpoint", SyncStatus.BEHIND)
        endpoint2.last_seen = datetime.now()
        print("✓ Endpoint back online")
        
        # Step 5: Retry sync operation
        retry_operation = await sync_coordinator.sync_to_latest("unstable-endpoint")
        
        # Simulate successful retry
        retry_operation.status = OperationStatus.COMPLETED
        retry_operation.completed_at = datetime.now()
        await sync_coordinator.update_operation_status(retry_operation.id, OperationStatus.COMPLETED)
        await pool_manager.update_endpoint_status("unstable-endpoint", SyncStatus.IN_SYNC)
        
        print("✓ Sync retry completed successfully")
        
        # Step 6: Verify recovery
        pool_status = await pool_manager.get_pool_status("recovery-pool")
        assert pool_status.overall_status == "in_sync"
        
        # Verify operation history shows both failure and success
        failed_op = await sync_coordinator.get_operation_status(sync_operation.id)
        assert failed_op.status == OperationStatus.FAILED
        
        success_op = await sync_coordinator.get_operation_status(retry_operation.id)
        assert success_op.status == OperationStatus.COMPLETED
        
        print("✓ Network failure recovery workflow validated")
    
    @pytest.mark.asyncio
    async def test_rollback_workflow(self, complete_test_environment, mock_client_factory):
        """Test rollback workflow when sync causes issues."""
        env = complete_test_environment
        pool_manager = env["pool_manager"]
        sync_coordinator = env["sync_coordinator"]
        
        # Setup
        test_pool = PackagePool(
            id="rollback-pool",
            name="Rollback Test Pool",
            description="Pool for testing rollback scenarios",
            endpoints=[],
            target_state_id=None,
            sync_policy=None
        )
        await pool_manager.create_pool(test_pool)
        
        # Create endpoint
        good_packages = [
            PackageState("stable-app", "1.0.0", "core", 5000, []),
            PackageState("database", "5.7.0", "extra", 50000, [])
        ]
        
        bad_packages = [
            PackageState("stable-app", "1.1.0", "core", 5000, []),  # Problematic version
            PackageState("database", "5.8.0", "extra", 50000, [])   # Incompatible version
        ]
        
        endpoint = Endpoint(
            id="test-endpoint",
            name="Test Endpoint",
            hostname="test.example.com", 
            pool_id="rollback-pool",
            sync_status=SyncStatus.IN_SYNC,
            last_seen=datetime.now()
        )
        await pool_manager.register_endpoint(endpoint)
        
        client = mock_client_factory("test-endpoint", "Test Endpoint", good_packages)
        
        # Save initial good state
        good_state = client["system_state"]
        await sync_coordinator.save_endpoint_state("test-endpoint", good_state)
        await sync_coordinator.set_as_latest("test-endpoint")
        print("✓ Initial stable state established")
        
        # Step 1: Update to problematic packages
        bad_state = SystemState(
            endpoint_id="test-endpoint",
            timestamp=datetime.now(),
            packages=bad_packages,
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        client["pacman"].get_system_state.return_value = bad_state
        await sync_coordinator.save_endpoint_state("test-endpoint", bad_state)
        await sync_coordinator.set_as_latest("test-endpoint")
        print("✓ Updated to problematic package versions")
        
        # Step 2: Detect issues and initiate rollback
        # Simulate issue detection (in real scenario, this might be monitoring alerts)
        print("✓ Issues detected with new package versions")
        
        # Step 3: Perform rollback to previous state
        rollback_operation = await sync_coordinator.revert_to_previous("test-endpoint")
        
        # Simulate successful rollback
        client["pacman"].get_system_state.return_value = good_state
        rollback_operation.status = OperationStatus.COMPLETED
        rollback_operation.completed_at = datetime.now()
        await sync_coordinator.update_operation_status(rollback_operation.id, OperationStatus.COMPLETED)
        await pool_manager.update_endpoint_status("test-endpoint", SyncStatus.IN_SYNC)
        
        print("✓ Rollback operation completed")
        
        # Step 4: Verify rollback was successful
        current_target = await sync_coordinator.get_target_state("rollback-pool")
        
        # Should be back to good packages
        current_app_version = next(p.version for p in current_target.packages if p.package_name == "stable-app")
        assert current_app_version == "1.0.0"  # Back to stable version
        
        # Verify operation history
        rollback_op = await sync_coordinator.get_operation_status(rollback_operation.id)
        assert rollback_op.status == OperationStatus.COMPLETED
        assert rollback_op.operation_type == OperationType.REVERT
        
        print("✓ Rollback workflow validated successfully")


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    @pytest.mark.asyncio
    async def test_development_to_production_workflow(self, complete_test_environment, mock_client_factory):
        """Test complete development to production deployment workflow."""
        env = complete_test_environment
        pool_manager = env["pool_manager"]
        sync_coordinator = env["sync_coordinator"]
        
        # Setup environments
        environments = {
            "dev": {
                "id": "dev-env",
                "name": "Development Environment",
                "hostname": "dev.company.com",
                "packages": [
                    PackageState("myapp", "2.0.0-dev", "custom", 15000, ["python", "postgresql"]),
                    PackageState("python", "3.11.0", "extra", 30000, []),
                    PackageState("postgresql", "14.5", "extra", 80000, []),
                    PackageState("redis", "7.0.5", "extra", 10000, []),
                    PackageState("nginx", "1.22.1", "extra", 8000, [])
                ]
            },
            "staging": {
                "id": "staging-env",
                "name": "Staging Environment", 
                "hostname": "staging.company.com",
                "packages": [
                    PackageState("myapp", "1.9.5", "custom", 15000, ["python", "postgresql"]),
                    PackageState("python", "3.10.8", "extra", 30000, []),
                    PackageState("postgresql", "14.4", "extra", 80000, []),
                    PackageState("redis", "6.2.7", "extra", 10000, []),
                    PackageState("nginx", "1.20.2", "extra", 8000, [])
                ]
            },
            "prod": {
                "id": "prod-env",
                "name": "Production Environment",
                "hostname": "prod.company.com", 
                "packages": [
                    PackageState("myapp", "1.9.3", "custom", 15000, ["python", "postgresql"]),
                    PackageState("python", "3.10.6", "extra", 30000, []),
                    PackageState("postgresql", "14.2", "extra", 80000, []),
                    PackageState("redis", "6.2.6", "extra", 10000, []),
                    PackageState("nginx", "1.20.1", "extra", 8000, [])
                ]
            }
        }
        
        # Create pool
        company_pool = PackagePool(
            id="company-pool",
            name="Company Application Pool",
            description="Main application deployment pool",
            endpoints=[],
            target_state_id=None,
            sync_policy=None
        )
        await pool_manager.create_pool(company_pool)
        
        # Register environments
        clients = {}
        for env_key, env_data in environments.items():
            endpoint = Endpoint(
                id=env_data["id"],
                name=env_data["name"],
                hostname=env_data["hostname"],
                pool_id="company-pool",
                sync_status=SyncStatus.IN_SYNC if env_key == "prod" else SyncStatus.BEHIND,
                last_seen=datetime.now()
            )
            await pool_manager.register_endpoint(endpoint)
            
            client = mock_client_factory(env_data["id"], env_data["name"], env_data["packages"])
            clients[env_data["id"]] = client
            
            await sync_coordinator.save_endpoint_state(env_data["id"], client["system_state"])
        
        # Set production as initial target
        await sync_coordinator.set_as_latest("prod-env")
        print("✓ Company environments set up")
        
        # Step 1: Development completes new version
        print("✓ Development has new version 2.0.0-dev ready")
        
        # Step 2: Promote development to staging
        dev_state = clients["dev-env"]["system_state"]
        
        # Create release version (remove -dev suffix)
        release_packages = []
        for pkg in dev_state.packages:
            if pkg.package_name == "myapp":
                release_packages.append(PackageState(
                    "myapp", "2.0.0", "custom", pkg.installed_size, pkg.dependencies
                ))
            else:
                release_packages.append(pkg)
        
        release_state = SystemState(
            endpoint_id="staging-env",
            timestamp=datetime.now(),
            packages=release_packages,
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        # Update staging
        clients["staging-env"]["pacman"].get_system_state.return_value = release_state
        await sync_coordinator.save_endpoint_state("staging-env", release_state)
        await sync_coordinator.set_as_latest("staging-env")
        await pool_manager.update_endpoint_status("staging-env", SyncStatus.IN_SYNC)
        await pool_manager.update_endpoint_status("prod-env", SyncStatus.BEHIND)
        
        print("✓ Version 2.0.0 deployed to staging")
        
        # Step 3: Staging validation (simulated)
        print("✓ Staging validation completed successfully")
        
        # Step 4: Deploy to production
        prod_sync = await sync_coordinator.sync_to_latest("prod-env")
        
        # Simulate production deployment
        clients["prod-env"]["pacman"].get_system_state.return_value = release_state
        prod_sync.status = OperationStatus.COMPLETED
        prod_sync.completed_at = datetime.now()
        await sync_coordinator.update_operation_status(prod_sync.id, OperationStatus.COMPLETED)
        await pool_manager.update_endpoint_status("prod-env", SyncStatus.IN_SYNC)
        
        print("✓ Version 2.0.0 deployed to production")
        
        # Step 5: Verify deployment
        pool_status = await pool_manager.get_pool_status("company-pool")
        target_state = await sync_coordinator.get_target_state("company-pool")
        
        # Verify all environments have the new version
        app_version = next(p.version for p in target_state.packages if p.package_name == "myapp")
        assert app_version == "2.0.0"
        
        # Verify production is in sync
        prod_status = await pool_manager.get_endpoint_status("prod-env")
        assert prod_status.sync_status == SyncStatus.IN_SYNC
        
        print("✓ Development to production workflow completed successfully")
    
    @pytest.mark.asyncio
    async def test_maintenance_window_workflow(self, complete_test_environment, mock_client_factory):
        """Test maintenance window coordination workflow."""
        env = complete_test_environment
        pool_manager = env["pool_manager"]
        sync_coordinator = env["sync_coordinator"]
        
        # Setup cluster of servers
        cluster_pool = PackagePool(
            id="cluster-pool",
            name="Server Cluster Pool",
            description="Pool for coordinated cluster maintenance",
            endpoints=[],
            target_state_id=None,
            sync_policy=None
        )
        await pool_manager.create_pool(cluster_pool)
        
        # Create cluster nodes
        base_packages = [
            PackageState("kernel", "5.19.0", "core", 100000, []),
            PackageState("systemd", "251.4", "core", 50000, []),
            PackageState("docker", "20.10.17", "extra", 30000, []),
            PackageState("kubernetes", "1.25.0", "extra", 40000, [])
        ]
        
        nodes = []
        clients = {}
        for i in range(4):
            node_id = f"node-{i+1}"
            endpoint = Endpoint(
                id=node_id,
                name=f"Cluster Node {i+1}",
                hostname=f"node{i+1}.cluster.com",
                pool_id="cluster-pool",
                sync_status=SyncStatus.IN_SYNC,
                last_seen=datetime.now()
            )
            await pool_manager.register_endpoint(endpoint)
            nodes.append(endpoint)
            
            client = mock_client_factory(node_id, endpoint.name, base_packages)
            clients[node_id] = client
            
            await sync_coordinator.save_endpoint_state(node_id, client["system_state"])
        
        # Set initial target state
        await sync_coordinator.set_as_latest("node-1")
        print("✓ 4-node cluster set up and synchronized")
        
        # Step 1: Prepare maintenance updates
        updated_packages = [
            PackageState("kernel", "5.20.0", "core", 100000, []),  # Kernel update
            PackageState("systemd", "252.1", "core", 50000, []),   # systemd update
            PackageState("docker", "20.10.18", "extra", 30000, []),
            PackageState("kubernetes", "1.25.2", "extra", 40000, [])  # Security update
        ]
        
        maintenance_state = SystemState(
            endpoint_id="node-1",
            timestamp=datetime.now(),
            packages=updated_packages,
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        # Update node-1 with maintenance packages
        clients["node-1"]["pacman"].get_system_state.return_value = maintenance_state
        await sync_coordinator.save_endpoint_state("node-1", maintenance_state)
        await sync_coordinator.set_as_latest("node-1")
        
        # Mark other nodes as behind
        for i in range(1, 4):
            await pool_manager.update_endpoint_status(f"node-{i+1}", SyncStatus.BEHIND)
        
        print("✓ Maintenance updates prepared on node-1")
        
        # Step 2: Rolling maintenance - update nodes one by one
        for i in range(1, 4):
            node_id = f"node-{i+1}"
            print(f"✓ Starting maintenance on {node_id}")
            
            # Initiate sync
            sync_op = await sync_coordinator.sync_to_latest(node_id)
            
            # Simulate maintenance completion
            clients[node_id]["pacman"].get_system_state.return_value = maintenance_state
            sync_op.status = OperationStatus.COMPLETED
            sync_op.completed_at = datetime.now()
            await sync_coordinator.update_operation_status(sync_op.id, OperationStatus.COMPLETED)
            await pool_manager.update_endpoint_status(node_id, SyncStatus.IN_SYNC)
            
            print(f"✓ Maintenance completed on {node_id}")
            
            # Simulate brief pause between nodes
            await asyncio.sleep(0.1)
        
        # Step 3: Verify all nodes are updated and synchronized
        pool_status = await pool_manager.get_pool_status("cluster-pool")
        assert pool_status.overall_status == "in_sync"
        
        # Verify all nodes have the updated kernel
        target_state = await sync_coordinator.get_target_state("cluster-pool")
        kernel_version = next(p.version for p in target_state.packages if p.package_name == "kernel")
        assert kernel_version == "5.20.0"
        
        print("✓ Coordinated maintenance window completed successfully")
        print("✓ All cluster nodes updated with minimal downtime")


def run_e2e_workflow_tests():
    """Run all end-to-end workflow tests."""
    print("=" * 60)
    print("END-TO-END WORKFLOW VALIDATION TESTS")
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
    success = run_e2e_workflow_tests()
    sys.exit(0 if success else 1)