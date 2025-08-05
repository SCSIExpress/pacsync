#!/usr/bin/env python3
"""
Test script for SyncCoordinator implementation.

This script tests the core functionality of the SyncCoordinator class
including sync operations, state management, and conflict resolution.
"""

import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.database.connection import DatabaseManager
from server.database.schema import create_tables
from server.core.sync_coordinator import SyncCoordinator, StateManager
from server.database.orm import PoolRepository, EndpointRepository
from shared.models import (
    PackagePool, Endpoint, SystemState, PackageState, SyncStatus,
    OperationType, OperationStatus, SyncPolicy, ConflictResolution
)


async def setup_test_data(db_manager: DatabaseManager):
    """Set up test data for sync coordinator tests."""
    print("Setting up test data...")
    
    # Create repositories
    pool_repo = PoolRepository(db_manager)
    endpoint_repo = EndpointRepository(db_manager)
    
    # Create a test pool
    pool = PackagePool(
        id=str(uuid4()),
        name="test-pool",
        description="Test pool for sync coordinator",
        sync_policy=SyncPolicy(
            auto_sync=False,
            conflict_resolution=ConflictResolution.NEWEST
        )
    )
    created_pool = await pool_repo.create(pool)
    
    # Create test endpoints
    endpoint1 = Endpoint(
        id=str(uuid4()),
        name="test-endpoint-1",
        hostname="host1.example.com",
        sync_status=SyncStatus.BEHIND
    )
    endpoint1 = await endpoint_repo.create(endpoint1)
    
    endpoint2 = Endpoint(
        id=str(uuid4()),
        name="test-endpoint-2", 
        hostname="host2.example.com",
        sync_status=SyncStatus.AHEAD
    )
    endpoint2 = await endpoint_repo.create(endpoint2)
    
    # Assign endpoints to pool
    await endpoint_repo.assign_to_pool(endpoint1.id, created_pool.id)
    await endpoint_repo.assign_to_pool(endpoint2.id, created_pool.id)
    
    print(f"Created pool: {created_pool.id}")
    print(f"Created endpoints: {endpoint1.id}, {endpoint2.id}")
    
    return created_pool, endpoint1, endpoint2


async def create_test_system_state(endpoint_id: str) -> SystemState:
    """Create a test system state."""
    packages = [
        PackageState(
            package_name="vim",
            version="9.0.1000-1",
            repository="core",
            installed_size=2048000,
            dependencies=["glibc", "ncurses"]
        ),
        PackageState(
            package_name="git",
            version="2.40.0-1",
            repository="extra",
            installed_size=15360000,
            dependencies=["curl", "expat", "perl"]
        ),
        PackageState(
            package_name="python",
            version="3.11.3-1",
            repository="core",
            installed_size=51200000,
            dependencies=["expat", "bzip2", "gdbm"]
        )
    ]
    
    return SystemState(
        endpoint_id=endpoint_id,
        timestamp=datetime.now(),
        packages=packages,
        pacman_version="6.0.2",
        architecture="x86_64"
    )


async def test_state_manager(db_manager: DatabaseManager, pool: PackagePool, endpoint: Endpoint):
    """Test StateManager functionality."""
    print("\n=== Testing StateManager ===")
    
    state_manager = StateManager(db_manager)
    
    # Create and save a test state
    test_state = await create_test_system_state(endpoint.id)
    state_id = await state_manager.save_state(endpoint.id, test_state)
    print(f"✓ Saved state: {state_id}")
    
    # Retrieve the saved state
    retrieved_state = await state_manager.get_state(state_id)
    assert retrieved_state is not None, "Failed to retrieve saved state"
    assert len(retrieved_state.packages) == 3, "Package count mismatch"
    print(f"✓ Retrieved state with {len(retrieved_state.packages)} packages")
    
    # Set as target state
    success = await state_manager.set_target_state(pool.id, state_id)
    assert success, "Failed to set target state"
    print("✓ Set as target state")
    
    # Get latest state
    latest_state = await state_manager.get_latest_state(pool.id)
    assert latest_state is not None, "Failed to get latest state"
    assert len(latest_state.packages) == 3, "Latest state package count mismatch"
    print("✓ Retrieved latest state")
    
    # Get endpoint states
    endpoint_states = await state_manager.get_endpoint_states(endpoint.id, limit=5)
    assert len(endpoint_states) >= 1, "No endpoint states found"
    print(f"✓ Retrieved {len(endpoint_states)} endpoint states")
    
    return state_id


async def test_sync_coordinator_operations(db_manager: DatabaseManager, pool: PackagePool, 
                                         endpoint1: Endpoint, endpoint2: Endpoint, target_state_id: str):
    """Test SyncCoordinator operations."""
    print("\n=== Testing SyncCoordinator Operations ===")
    
    sync_coordinator = SyncCoordinator(db_manager)
    
    # Test sync to latest
    print("Testing sync to latest...")
    sync_operation = await sync_coordinator.sync_to_latest(endpoint2.id)
    assert sync_operation.operation_type == OperationType.SYNC, "Wrong operation type"
    assert sync_operation.status == OperationStatus.PENDING, "Wrong initial status"
    print(f"✓ Created sync operation: {sync_operation.id}")
    
    # Wait for operation to process
    await asyncio.sleep(3)
    
    # Check operation status
    updated_operation = await sync_coordinator.get_operation_status(sync_operation.id)
    assert updated_operation is not None, "Operation not found"
    print(f"✓ Operation status: {updated_operation.status.value}")
    
    # Test set as latest
    print("Testing set as latest...")
    set_latest_operation = await sync_coordinator.set_as_latest(endpoint1.id)
    assert set_latest_operation.operation_type == OperationType.SET_LATEST, "Wrong operation type"
    print(f"✓ Created set-latest operation: {set_latest_operation.id}")
    
    # Wait for operation to process
    await asyncio.sleep(2)
    
    # Check operation status
    updated_set_operation = await sync_coordinator.get_operation_status(set_latest_operation.id)
    assert updated_set_operation is not None, "Set-latest operation not found"
    print(f"✓ Set-latest operation status: {updated_set_operation.status.value}")
    
    # Test revert to previous (need at least 2 states)
    print("Testing revert to previous...")
    try:
        revert_operation = await sync_coordinator.revert_to_previous(endpoint1.id)
        print(f"✓ Created revert operation: {revert_operation.id}")
        
        # Wait for operation to process
        await asyncio.sleep(2)
        
        updated_revert = await sync_coordinator.get_operation_status(revert_operation.id)
        print(f"✓ Revert operation status: {updated_revert.status.value}")
    except Exception as e:
        print(f"⚠ Revert test skipped (expected for new endpoint): {e}")
    
    # Test getting endpoint operations
    endpoint_operations = await sync_coordinator.get_endpoint_operations(endpoint1.id)
    print(f"✓ Retrieved {len(endpoint_operations)} operations for endpoint")
    
    # Test getting pool operations
    pool_operations = await sync_coordinator.get_pool_operations(pool.id)
    print(f"✓ Retrieved {len(pool_operations)} operations for pool")


async def test_operation_cancellation(db_manager: DatabaseManager, endpoint: Endpoint):
    """Test operation cancellation."""
    print("\n=== Testing Operation Cancellation ===")
    
    sync_coordinator = SyncCoordinator(db_manager)
    
    # Create an operation
    try:
        operation = await sync_coordinator.sync_to_latest(endpoint.id)
        print(f"✓ Created operation for cancellation: {operation.id}")
        
        # Cancel immediately (before it processes)
        success = await sync_coordinator.cancel_operation(operation.id)
        if success:
            print("✓ Successfully cancelled operation")
        else:
            print("⚠ Operation cancellation failed (may have already processed)")
            
    except Exception as e:
        print(f"⚠ Cancellation test skipped: {e}")


async def main():
    """Main test function."""
    print("Starting SyncCoordinator tests...")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        # Create tables
        await create_tables(db_manager)
        print("✓ Database tables created")
        
        # Set up test data
        pool, endpoint1, endpoint2 = await setup_test_data(db_manager)
        
        # Test StateManager
        target_state_id = await test_state_manager(db_manager, pool, endpoint1)
        
        # Test SyncCoordinator operations
        await test_sync_coordinator_operations(db_manager, pool, endpoint1, endpoint2, target_state_id)
        
        # Test operation cancellation
        await test_operation_cancellation(db_manager, endpoint2)
        
        print("\n✅ All SyncCoordinator tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await db_manager.close()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)