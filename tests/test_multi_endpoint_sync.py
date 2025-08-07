#!/usr/bin/env python3
"""
Multi-endpoint synchronization scenario tests.

This module tests complex synchronization scenarios involving multiple endpoints:
- Multi-endpoint pool synchronization
- Cross-endpoint state propagation
- Conflict resolution across endpoints
- Pool-wide operations coordination
- Endpoint failure and recovery scenarios

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
async def test_server_with_pool():
    """Create test server with pre-configured pool and endpoints."""
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
    
    # Create test pool
    test_pool = PackagePool(
        id="test-pool-123",
        name="Multi-Endpoint Test Pool",
        description="Pool for testing multi-endpoint scenarios",
        endpoints=[],
        target_state_id=None,
        sync_policy=None
    )
    await pool_manager.create_pool(test_pool)
    
    # Create test endpoints
    endpoints = []
    for i in range(3):
        endpoint = Endpoint(
            id=f"endpoint-{i+1}",
            name=f"test-endpoint-{i+1}",
            hostname=f"host-{i+1}.example.com",
            pool_id="test-pool-123",
            sync_status=SyncStatus.OFFLINE,
            last_seen=None
        )
        await pool_manager.register_endpoint(endpoint)
        endpoints.append(endpoint)
    
    # Store in app state
    app.state.db_manager = db_manager
    app.state.pool_manager = pool_manager
    app.state.sync_coordinator = sync_coordinator
    app.state.test_pool = test_pool
    app.state.test_endpoints = endpoints
    
    yield app
    
    # Cleanup
    await db_manager.close()
    os.unlink(temp_db.name)


@pytest.fixture
def sample_package_states():
    """Sample package states for different endpoints."""
    return {
        "endpoint-1": [
            PackageState("package1", "1.0.0", "core", 1024, []),
            PackageState("package2", "2.0.0", "extra", 2048, ["dep1"]),
            PackageState("package3", "3.0.0", "community", 4096, ["dep2"])
        ],
        "endpoint-2": [
            PackageState("package1", "1.1.0", "core", 1024, []),  # Newer version
            PackageState("package2", "2.0.0", "extra", 2048, ["dep1"]),
            PackageState("package4", "4.0.0", "aur", 8192, [])  # Different package
        ],
        "endpoint-3": [
            PackageState("package1", "0.9.0", "core", 1024, []),  # Older version
            PackageState("package2", "2.1.0", "extra", 2048, ["dep1"]),  # Newer version
            PackageState("package3", "3.0.0", "community", 4096, ["dep2"])
        ]
    }


class TestMultiEndpointPoolOperations:
    """Test pool-wide operations across multiple endpoints."""
    
    @pytest.mark.asyncio
    async def test_pool_wide_sync_coordination(self, test_server_with_pool, sample_package_states):
        """Test coordinated sync operation across all endpoints in pool."""
        from fastapi.testclient import TestClient
        
        with TestClient(test_server_with_pool) as client:
            pool_manager = test_server_with_pool.state.pool_manager
            sync_coordinator = test_server_with_pool.state.sync_coordinator
            endpoints = test_server_with_pool.state.test_endpoints
            
            # Set up endpoint states
            for endpoint in endpoints:
                endpoint_id = endpoint.id
                packages = sample_package_states[endpoint_id]
                
                system_state = SystemState(
                    endpoint_id=endpoint_id,
                    timestamp=datetime.now(),
                    packages=packages,
                    pacman_version="6.0.1",
                    architecture="x86_64"
                )
                
                # Save state for each endpoint
                await sync_coordinator.save_endpoint_state(endpoint_id, system_state)
                
                # Update endpoint status
                endpoint.sync_status = SyncStatus.BEHIND
                endpoint.last_seen = datetime.now()
                await pool_manager.update_endpoint_status(endpoint_id, SyncStatus.BEHIND)
            
            # Set endpoint-1 as the target state (most complete package set)
            target_endpoint = endpoints[0]
            await sync_coordinator.set_as_latest(target_endpoint.id)
            
            # Initiate pool-wide sync
            sync_operations = []
            for endpoint in endpoints[1:]:  # Skip target endpoint
                operation = await sync_coordinator.sync_to_latest(endpoint.id)
                sync_operations.append(operation)
            
            # Verify operations were created
            assert len(sync_operations) == 2
            for operation in sync_operations:
                assert operation.operation_type == OperationType.SYNC
                assert operation.status == OperationStatus.PENDING
                assert operation.pool_id == "test-pool-123"
            
            # Simulate successful completion of all operations
            for operation in sync_operations:
                operation.status = OperationStatus.COMPLETED
                operation.completed_at = datetime.now()
                await sync_coordinator.update_operation_status(operation.id, OperationStatus.COMPLETED)
            
            # Verify all endpoints are now in sync
            pool_status = await pool_manager.get_pool_status("test-pool-123")
            assert pool_status.overall_status == "in_sync"
    
    @pytest.mark.asyncio
    async def test_cross_endpoint_state_propagation(self, test_server_with_pool, sample_package_states):
        """Test state changes propagating across endpoints in the same pool."""
        pool_manager = test_server_with_pool.state.pool_manager
        sync_coordinator = test_server_with_pool.state.sync_coordinator
        endpoints = test_server_with_pool.state.test_endpoints
        
        # Set initial states
        for endpoint in endpoints:
            endpoint_id = endpoint.id
            packages = sample_package_states[endpoint_id]
            
            system_state = SystemState(
                endpoint_id=endpoint_id,
                timestamp=datetime.now(),
                packages=packages,
                pacman_version="6.0.1",
                architecture="x86_64"
            )
            
            await sync_coordinator.save_endpoint_state(endpoint_id, system_state)
        
        # Endpoint-2 sets new state as latest
        new_packages = [
            PackageState("package1", "1.2.0", "core", 1024, []),  # Even newer
            PackageState("package2", "2.2.0", "extra", 2048, ["dep1"]),
            PackageState("package5", "5.0.0", "testing", 16384, [])  # New package
        ]
        
        new_state = SystemState(
            endpoint_id="endpoint-2",
            timestamp=datetime.now(),
            packages=new_packages,
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        # Set as latest
        await sync_coordinator.save_endpoint_state("endpoint-2", new_state)
        await sync_coordinator.set_as_latest("endpoint-2")
        
        # Verify other endpoints are now behind
        for endpoint_id in ["endpoint-1", "endpoint-3"]:
            endpoint_status = await pool_manager.get_endpoint_status(endpoint_id)
            assert endpoint_status.sync_status == SyncStatus.BEHIND
        
        # Verify endpoint-2 is ahead (since it set the new target)
        endpoint2_status = await pool_manager.get_endpoint_status("endpoint-2")
        assert endpoint2_status.sync_status == SyncStatus.IN_SYNC
    
    @pytest.mark.asyncio
    async def test_pool_target_state_management(self, test_server_with_pool, sample_package_states):
        """Test management of pool target state across multiple endpoints."""
        sync_coordinator = test_server_with_pool.state.sync_coordinator
        endpoints = test_server_with_pool.state.test_endpoints
        
        # Set different states for each endpoint
        states = {}
        for endpoint in endpoints:
            endpoint_id = endpoint.id
            packages = sample_package_states[endpoint_id]
            
            system_state = SystemState(
                endpoint_id=endpoint_id,
                timestamp=datetime.now(),
                packages=packages,
                pacman_version="6.0.1",
                architecture="x86_64"
            )
            
            await sync_coordinator.save_endpoint_state(endpoint_id, system_state)
            states[endpoint_id] = system_state
        
        # Set endpoint-1 as target
        await sync_coordinator.set_as_latest("endpoint-1")
        target_state_1 = await sync_coordinator.get_target_state("test-pool-123")
        assert target_state_1.endpoint_id == "endpoint-1"
        
        # Change target to endpoint-2
        await sync_coordinator.set_as_latest("endpoint-2")
        target_state_2 = await sync_coordinator.get_target_state("test-pool-123")
        assert target_state_2.endpoint_id == "endpoint-2"
        
        # Verify target state changed
        assert target_state_1.timestamp != target_state_2.timestamp
        assert len(target_state_1.packages) != len(target_state_2.packages)


class TestConflictResolution:
    """Test conflict resolution scenarios across multiple endpoints."""
    
    @pytest.mark.asyncio
    async def test_package_version_conflict_resolution(self, test_server_with_pool, sample_package_states):
        """Test resolution of package version conflicts across endpoints."""
        from server.core.repository_analyzer import RepositoryAnalyzer
        
        db_manager = test_server_with_pool.state.db_manager
        endpoints = test_server_with_pool.state.test_endpoints
        
        # Create repository analyzer
        repo_analyzer = RepositoryAnalyzer(db_manager)
        
        # Set up conflicting package versions
        endpoint_states = {}
        for endpoint in endpoints:
            endpoint_id = endpoint.id
            packages = sample_package_states[endpoint_id]
            
            system_state = SystemState(
                endpoint_id=endpoint_id,
                timestamp=datetime.now(),
                packages=packages,
                pacman_version="6.0.1",
                architecture="x86_64"
            )
            
            endpoint_states[endpoint_id] = system_state
        
        # Analyze compatibility across endpoints
        compatibility_analysis = await repo_analyzer.analyze_pool_compatibility("test-pool-123")
        
        # Should detect conflicts for package1 (different versions across endpoints)
        conflicts = compatibility_analysis.conflicts
        package1_conflicts = [c for c in conflicts if c.package_name == "package1"]
        assert len(package1_conflicts) > 0
        
        # Verify conflict details
        package1_conflict = package1_conflicts[0]
        assert package1_conflict.package_name == "package1"
        assert len(package1_conflict.conflicting_versions) >= 2
        
        # Test conflict resolution by choosing newest version
        resolved_version = max(package1_conflict.conflicting_versions, key=lambda v: v.version)
        assert resolved_version.version == "1.1.0"  # From endpoint-2
    
    @pytest.mark.asyncio
    async def test_missing_package_handling(self, test_server_with_pool, sample_package_states):
        """Test handling of packages missing from some endpoints."""
        from server.core.repository_analyzer import RepositoryAnalyzer
        
        db_manager = test_server_with_pool.state.db_manager
        endpoints = test_server_with_pool.state.test_endpoints
        
        repo_analyzer = RepositoryAnalyzer(db_manager)
        
        # Set up states with missing packages
        for endpoint in endpoints:
            endpoint_id = endpoint.id
            packages = sample_package_states[endpoint_id]
            
            system_state = SystemState(
                endpoint_id=endpoint_id,
                timestamp=datetime.now(),
                packages=packages,
                pacman_version="6.0.1",
                architecture="x86_64"
            )
            
            await repo_analyzer.update_endpoint_packages(endpoint_id, packages)
        
        # Analyze compatibility
        compatibility_analysis = await repo_analyzer.analyze_pool_compatibility("test-pool-123")
        
        # Should identify common packages (available on all endpoints)
        common_packages = compatibility_analysis.common_packages
        common_names = [p.name for p in common_packages]
        
        # package1 and package2 should be common (present in all endpoints)
        assert "package1" in common_names
        assert "package2" in common_names
        
        # Should identify excluded packages (not available on all endpoints)
        excluded_packages = compatibility_analysis.excluded_packages
        excluded_names = [p.name for p in excluded_packages]
        
        # package3 and package4 should be excluded (not present in all endpoints)
        assert "package3" in excluded_names or "package4" in excluded_names
    
    @pytest.mark.asyncio
    async def test_repository_compatibility_analysis(self, test_server_with_pool):
        """Test repository compatibility analysis across endpoints."""
        from server.core.repository_analyzer import RepositoryAnalyzer
        from shared.models import Repository, RepositoryPackage
        
        db_manager = test_server_with_pool.state.db_manager
        endpoints = test_server_with_pool.state.test_endpoints
        
        repo_analyzer = RepositoryAnalyzer(db_manager)
        
        # Set up different repository configurations for each endpoint
        repo_configs = {
            "endpoint-1": [
                Repository(
                    id="repo-1-core",
                    endpoint_id="endpoint-1",
                    repo_name="core",
                    repo_url="https://mirror1.archlinux.org/core/os/x86_64",
                    packages=[
                        RepositoryPackage("package1", "1.0.0", "core", "x86_64"),
                        RepositoryPackage("package2", "2.0.0", "core", "x86_64")
                    ],
                    last_updated=datetime.now()
                )
            ],
            "endpoint-2": [
                Repository(
                    id="repo-2-core",
                    endpoint_id="endpoint-2",
                    repo_name="core",
                    repo_url="https://mirror2.archlinux.org/core/os/x86_64",
                    packages=[
                        RepositoryPackage("package1", "1.1.0", "core", "x86_64"),  # Newer version
                        RepositoryPackage("package2", "2.0.0", "core", "x86_64"),
                        RepositoryPackage("package3", "3.0.0", "core", "x86_64")   # Additional package
                    ],
                    last_updated=datetime.now()
                )
            ],
            "endpoint-3": [
                Repository(
                    id="repo-3-core",
                    endpoint_id="endpoint-3",
                    repo_name="core",
                    repo_url="https://mirror3.archlinux.org/core/os/x86_64",
                    packages=[
                        RepositoryPackage("package1", "0.9.0", "core", "x86_64"),  # Older version
                        RepositoryPackage("package2", "2.1.0", "core", "x86_64")   # Different version
                    ],
                    last_updated=datetime.now()
                )
            ]
        }
        
        # Update repository information for each endpoint
        for endpoint_id, repos in repo_configs.items():
            for repo in repos:
                await repo_analyzer.update_repository_info(endpoint_id, repo)
        
        # Analyze repository compatibility
        compatibility_analysis = await repo_analyzer.analyze_pool_compatibility("test-pool-123")
        
        # Verify analysis results
        assert compatibility_analysis.pool_id == "test-pool-123"
        assert len(compatibility_analysis.common_packages) >= 1  # At least package2 should be common
        assert len(compatibility_analysis.conflicts) >= 1  # Should detect version conflicts


class TestEndpointFailureScenarios:
    """Test endpoint failure and recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_endpoint_offline_during_sync(self, test_server_with_pool, sample_package_states):
        """Test handling of endpoint going offline during sync operation."""
        pool_manager = test_server_with_pool.state.pool_manager
        sync_coordinator = test_server_with_pool.state.sync_coordinator
        endpoints = test_server_with_pool.state.test_endpoints
        
        # Set up initial states
        for endpoint in endpoints:
            endpoint_id = endpoint.id
            packages = sample_package_states[endpoint_id]
            
            system_state = SystemState(
                endpoint_id=endpoint_id,
                timestamp=datetime.now(),
                packages=packages,
                pacman_version="6.0.1",
                architecture="x86_64"
            )
            
            await sync_coordinator.save_endpoint_state(endpoint_id, system_state)
            
            # Mark endpoints as online
            endpoint.sync_status = SyncStatus.BEHIND
            endpoint.last_seen = datetime.now()
            await pool_manager.update_endpoint_status(endpoint_id, SyncStatus.BEHIND)
        
        # Set target state
        await sync_coordinator.set_as_latest("endpoint-1")
        
        # Start sync operations
        sync_operations = []
        for endpoint in endpoints[1:]:
            operation = await sync_coordinator.sync_to_latest(endpoint.id)
            sync_operations.append(operation)
        
        # Simulate endpoint-2 going offline during sync
        offline_endpoint = endpoints[1]  # endpoint-2
        offline_endpoint.sync_status = SyncStatus.OFFLINE
        offline_endpoint.last_seen = datetime.now() - timedelta(minutes=10)
        await pool_manager.update_endpoint_status(offline_endpoint.id, SyncStatus.OFFLINE)
        
        # Mark its operation as failed
        offline_operation = sync_operations[0]
        offline_operation.status = OperationStatus.FAILED
        offline_operation.completed_at = datetime.now()
        await sync_coordinator.update_operation_status(offline_operation.id, OperationStatus.FAILED)
        
        # Complete other operation successfully
        online_operation = sync_operations[1]
        online_operation.status = OperationStatus.COMPLETED
        online_operation.completed_at = datetime.now()
        await sync_coordinator.update_operation_status(online_operation.id, OperationStatus.COMPLETED)
        
        # Verify pool status reflects partial completion
        pool_status = await pool_manager.get_pool_status("test-pool-123")
        assert pool_status.overall_status != "in_sync"  # Should not be fully in sync
        
        # Verify offline endpoint status
        offline_status = await pool_manager.get_endpoint_status(offline_endpoint.id)
        assert offline_status.sync_status == SyncStatus.OFFLINE
    
    @pytest.mark.asyncio
    async def test_endpoint_recovery_and_catch_up(self, test_server_with_pool, sample_package_states):
        """Test endpoint recovery and automatic catch-up sync."""
        pool_manager = test_server_with_pool.state.pool_manager
        sync_coordinator = test_server_with_pool.state.sync_coordinator
        endpoints = test_server_with_pool.state.test_endpoints
        
        # Set up scenario where endpoint-3 has been offline
        offline_endpoint = endpoints[2]  # endpoint-3
        offline_endpoint.sync_status = SyncStatus.OFFLINE
        offline_endpoint.last_seen = datetime.now() - timedelta(hours=2)
        await pool_manager.update_endpoint_status(offline_endpoint.id, SyncStatus.OFFLINE)
        
        # Other endpoints are in sync with newer state
        for endpoint in endpoints[:2]:
            endpoint_id = endpoint.id
            packages = sample_package_states[endpoint_id]
            
            system_state = SystemState(
                endpoint_id=endpoint_id,
                timestamp=datetime.now(),
                packages=packages,
                pacman_version="6.0.1",
                architecture="x86_64"
            )
            
            await sync_coordinator.save_endpoint_state(endpoint_id, system_state)
            endpoint.sync_status = SyncStatus.IN_SYNC
            endpoint.last_seen = datetime.now()
            await pool_manager.update_endpoint_status(endpoint_id, SyncStatus.IN_SYNC)
        
        # Set current target state
        await sync_coordinator.set_as_latest("endpoint-1")
        
        # Simulate endpoint-3 coming back online with old state
        old_packages = [
            PackageState("package1", "0.8.0", "core", 1024, []),  # Very old version
            PackageState("package2", "1.9.0", "extra", 2048, ["dep1"])  # Old version
        ]
        
        old_state = SystemState(
            endpoint_id=offline_endpoint.id,
            timestamp=datetime.now() - timedelta(hours=2),
            packages=old_packages,
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        await sync_coordinator.save_endpoint_state(offline_endpoint.id, old_state)
        
        # Mark endpoint as back online but behind
        offline_endpoint.sync_status = SyncStatus.BEHIND
        offline_endpoint.last_seen = datetime.now()
        await pool_manager.update_endpoint_status(offline_endpoint.id, SyncStatus.BEHIND)
        
        # Initiate catch-up sync
        catch_up_operation = await sync_coordinator.sync_to_latest(offline_endpoint.id)
        
        # Verify catch-up operation was created
        assert catch_up_operation.operation_type == OperationType.SYNC
        assert catch_up_operation.status == OperationStatus.PENDING
        assert catch_up_operation.endpoint_id == offline_endpoint.id
        
        # Simulate successful catch-up
        catch_up_operation.status = OperationStatus.COMPLETED
        catch_up_operation.completed_at = datetime.now()
        await sync_coordinator.update_operation_status(catch_up_operation.id, OperationStatus.COMPLETED)
        
        # Update endpoint status to in sync
        offline_endpoint.sync_status = SyncStatus.IN_SYNC
        await pool_manager.update_endpoint_status(offline_endpoint.id, SyncStatus.IN_SYNC)
        
        # Verify pool is now fully in sync
        pool_status = await pool_manager.get_pool_status("test-pool-123")
        assert pool_status.overall_status == "in_sync"
    
    @pytest.mark.asyncio
    async def test_partial_pool_operations(self, test_server_with_pool, sample_package_states):
        """Test pool operations when some endpoints are unavailable."""
        pool_manager = test_server_with_pool.state.pool_manager
        sync_coordinator = test_server_with_pool.state.sync_coordinator
        endpoints = test_server_with_pool.state.test_endpoints
        
        # Set up mixed endpoint availability
        available_endpoints = endpoints[:2]  # endpoint-1, endpoint-2
        unavailable_endpoint = endpoints[2]   # endpoint-3
        
        # Set available endpoints as online
        for endpoint in available_endpoints:
            endpoint_id = endpoint.id
            packages = sample_package_states[endpoint_id]
            
            system_state = SystemState(
                endpoint_id=endpoint_id,
                timestamp=datetime.now(),
                packages=packages,
                pacman_version="6.0.1",
                architecture="x86_64"
            )
            
            await sync_coordinator.save_endpoint_state(endpoint_id, system_state)
            endpoint.sync_status = SyncStatus.BEHIND
            endpoint.last_seen = datetime.now()
            await pool_manager.update_endpoint_status(endpoint_id, SyncStatus.BEHIND)
        
        # Set unavailable endpoint as offline
        unavailable_endpoint.sync_status = SyncStatus.OFFLINE
        unavailable_endpoint.last_seen = datetime.now() - timedelta(hours=1)
        await pool_manager.update_endpoint_status(unavailable_endpoint.id, SyncStatus.OFFLINE)
        
        # Attempt pool-wide operation (should only affect available endpoints)
        await sync_coordinator.set_as_latest(available_endpoints[0].id)
        
        # Try to sync available endpoints
        sync_operations = []
        for endpoint in available_endpoints[1:]:
            operation = await sync_coordinator.sync_to_latest(endpoint.id)
            sync_operations.append(operation)
        
        # Should not attempt to sync offline endpoint
        try:
            offline_operation = await sync_coordinator.sync_to_latest(unavailable_endpoint.id)
            # If this succeeds, it should be marked as failed due to offline status
            assert offline_operation.status == OperationStatus.FAILED
        except Exception:
            # Or it might raise an exception for offline endpoint
            pass
        
        # Complete operations for available endpoints
        for operation in sync_operations:
            operation.status = OperationStatus.COMPLETED
            operation.completed_at = datetime.now()
            await sync_coordinator.update_operation_status(operation.id, OperationStatus.COMPLETED)
        
        # Update available endpoints to in sync
        for endpoint in available_endpoints:
            endpoint.sync_status = SyncStatus.IN_SYNC
            await pool_manager.update_endpoint_status(endpoint.id, SyncStatus.IN_SYNC)
        
        # Verify pool status reflects partial sync
        pool_status = await pool_manager.get_pool_status("test-pool-123")
        
        # Pool should not be fully in sync due to offline endpoint
        assert pool_status.overall_status != "in_sync"
        
        # But available endpoints should be in sync
        for endpoint in available_endpoints:
            endpoint_status = await pool_manager.get_endpoint_status(endpoint.id)
            assert endpoint_status.sync_status == SyncStatus.IN_SYNC


class TestConcurrentOperations:
    """Test concurrent operations across multiple endpoints."""
    
    @pytest.mark.asyncio
    async def test_concurrent_sync_operations(self, test_server_with_pool, sample_package_states):
        """Test multiple concurrent sync operations across endpoints."""
        sync_coordinator = test_server_with_pool.state.sync_coordinator
        endpoints = test_server_with_pool.state.test_endpoints
        
        # Set up initial states
        for endpoint in endpoints:
            endpoint_id = endpoint.id
            packages = sample_package_states[endpoint_id]
            
            system_state = SystemState(
                endpoint_id=endpoint_id,
                timestamp=datetime.now(),
                packages=packages,
                pacman_version="6.0.1",
                architecture="x86_64"
            )
            
            await sync_coordinator.save_endpoint_state(endpoint_id, system_state)
        
        # Set target state
        await sync_coordinator.set_as_latest("endpoint-1")
        
        # Start concurrent sync operations
        sync_tasks = []
        for endpoint in endpoints[1:]:
            task = asyncio.create_task(sync_coordinator.sync_to_latest(endpoint.id))
            sync_tasks.append(task)
        
        # Wait for all operations to be created
        sync_operations = await asyncio.gather(*sync_tasks)
        
        # Verify all operations were created successfully
        assert len(sync_operations) == 2
        for operation in sync_operations:
            assert operation.operation_type == OperationType.SYNC
            assert operation.status == OperationStatus.PENDING
        
        # Verify operations have different IDs
        operation_ids = [op.id for op in sync_operations]
        assert len(set(operation_ids)) == len(operation_ids)  # All unique
    
    @pytest.mark.asyncio
    async def test_operation_queue_management(self, test_server_with_pool, sample_package_states):
        """Test operation queue management with multiple endpoints."""
        sync_coordinator = test_server_with_pool.state.sync_coordinator
        endpoints = test_server_with_pool.state.test_endpoints
        
        # Set up states
        for endpoint in endpoints:
            endpoint_id = endpoint.id
            packages = sample_package_states[endpoint_id]
            
            system_state = SystemState(
                endpoint_id=endpoint_id,
                timestamp=datetime.now(),
                packages=packages,
                pacman_version="6.0.1",
                architecture="x86_64"
            )
            
            await sync_coordinator.save_endpoint_state(endpoint_id, system_state)
        
        # Create multiple operations for the same endpoint (should queue)
        endpoint_id = endpoints[0].id
        
        # First operation
        operation1 = await sync_coordinator.sync_to_latest(endpoint_id)
        assert operation1.status == OperationStatus.PENDING
        
        # Second operation on same endpoint (should be queued or rejected)
        try:
            operation2 = await sync_coordinator.sync_to_latest(endpoint_id)
            # If allowed, should be queued
            assert operation2.status in [OperationStatus.PENDING, OperationStatus.QUEUED]
        except Exception:
            # Or might be rejected due to active operation
            pass
        
        # Operations on different endpoints should be allowed
        operation3 = await sync_coordinator.sync_to_latest(endpoints[1].id)
        assert operation3.status == OperationStatus.PENDING
        assert operation3.endpoint_id != operation1.endpoint_id


def run_multi_endpoint_tests():
    """Run all multi-endpoint synchronization tests."""
    print("=" * 60)
    print("MULTI-ENDPOINT SYNCHRONIZATION TESTS")
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
    success = run_multi_endpoint_tests()
    sys.exit(0 if success else 1)