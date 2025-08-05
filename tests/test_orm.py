#!/usr/bin/env python3
"""
Test script for ORM layer implementation.

This script tests the database operations (CRUD) for all core entities
to verify data integrity and business rules validation.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from server.database.connection import DatabaseManager
from server.database.schema import create_tables, drop_tables
from server.database.orm import ORMManager, ValidationError, NotFoundError
from shared.models import (
    PackagePool, Endpoint, SystemState, PackageState, SyncOperation,
    Repository, RepositoryPackage, SyncStatus, OperationType, OperationStatus,
    SyncPolicy, ConflictResolution
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_pool_operations(orm: ORMManager):
    """Test PackagePool CRUD operations."""
    logger.info("Testing PackagePool operations...")
    
    # Test create
    pool = PackagePool(
        id="test-pool-1",
        name="Test Pool",
        description="A test pool for validation",
        sync_policy=SyncPolicy(
            auto_sync=True,
            exclude_packages=["test-pkg"],
            include_aur=False,
            conflict_resolution=ConflictResolution.NEWEST
        )
    )
    
    created_pool = await orm.pools.create(pool)
    assert created_pool.name == "Test Pool"
    assert created_pool.sync_policy.auto_sync == True
    logger.info("✓ Pool creation successful")
    
    # Test duplicate name validation
    try:
        duplicate_pool = PackagePool(
            id="test-pool-2",
            name="Test Pool",  # Same name
            description="Duplicate name test"
        )
        await orm.pools.create(duplicate_pool)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        logger.info("✓ Duplicate name validation working")
    
    # Test get by ID
    retrieved_pool = await orm.pools.get_by_id("test-pool-1")
    assert retrieved_pool is not None
    assert retrieved_pool.name == "Test Pool"
    logger.info("✓ Pool retrieval by ID successful")
    
    # Test get by name
    retrieved_pool = await orm.pools.get_by_name("Test Pool")
    assert retrieved_pool is not None
    assert retrieved_pool.id == "test-pool-1"
    logger.info("✓ Pool retrieval by name successful")
    
    # Test update
    updated_pool = await orm.pools.update(
        "test-pool-1",
        description="Updated description",
        sync_policy={
            "auto_sync": False,
            "exclude_packages": ["updated-pkg"],
            "include_aur": True,
            "conflict_resolution": "manual"
        }
    )
    assert updated_pool.description == "Updated description"
    assert updated_pool.sync_policy.auto_sync == False
    assert updated_pool.sync_policy.include_aur == True
    logger.info("✓ Pool update successful")
    
    # Test list all
    all_pools = await orm.pools.list_all()
    assert len(all_pools) >= 1
    logger.info("✓ Pool listing successful")
    
    return created_pool


async def test_endpoint_operations(orm: ORMManager, pool: PackagePool):
    """Test Endpoint CRUD operations."""
    logger.info("Testing Endpoint operations...")
    
    # Test create
    endpoint = Endpoint(
        id="test-endpoint-1",
        name="Test Endpoint",
        hostname="test-host",
        sync_status=SyncStatus.OFFLINE
    )
    
    created_endpoint = await orm.endpoints.create(endpoint)
    assert created_endpoint.name == "Test Endpoint"
    assert created_endpoint.hostname == "test-host"
    assert created_endpoint.sync_status == SyncStatus.OFFLINE
    logger.info("✓ Endpoint creation successful")
    
    # Test duplicate name/hostname validation
    try:
        duplicate_endpoint = Endpoint(
            id="test-endpoint-2",
            name="Test Endpoint",  # Same name
            hostname="test-host"   # Same hostname
        )
        await orm.endpoints.create(duplicate_endpoint)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        logger.info("✓ Duplicate name/hostname validation working")
    
    # Test get by ID
    retrieved_endpoint = await orm.endpoints.get_by_id("test-endpoint-1")
    assert retrieved_endpoint is not None
    assert retrieved_endpoint.name == "Test Endpoint"
    logger.info("✓ Endpoint retrieval by ID successful")
    
    # Test assign to pool
    success = await orm.endpoints.assign_to_pool("test-endpoint-1", pool.id)
    assert success == True
    
    # Verify assignment
    retrieved_endpoint = await orm.endpoints.get_by_id("test-endpoint-1")
    assert retrieved_endpoint.pool_id == pool.id
    logger.info("✓ Endpoint pool assignment successful")
    
    # Test update status
    success = await orm.endpoints.update_status("test-endpoint-1", SyncStatus.IN_SYNC)
    assert success == True
    
    # Verify status update
    retrieved_endpoint = await orm.endpoints.get_by_id("test-endpoint-1")
    assert retrieved_endpoint.sync_status == SyncStatus.IN_SYNC
    logger.info("✓ Endpoint status update successful")
    
    # Test update last seen
    now = datetime.now()
    success = await orm.endpoints.update_last_seen("test-endpoint-1", now)
    assert success == True
    logger.info("✓ Endpoint last seen update successful")
    
    # Test list by pool
    pool_endpoints = await orm.endpoints.list_by_pool(pool.id)
    assert len(pool_endpoints) >= 1
    assert pool_endpoints[0].id == "test-endpoint-1"
    logger.info("✓ Endpoint listing by pool successful")
    
    return created_endpoint


async def test_package_state_operations(orm: ORMManager, pool: PackagePool, endpoint: Endpoint):
    """Test SystemState operations."""
    logger.info("Testing PackageState operations...")
    
    # Create test packages
    packages = [
        PackageState(
            package_name="test-package-1",
            version="1.0.0",
            repository="core",
            installed_size=1024,
            dependencies=["dep1", "dep2"]
        ),
        PackageState(
            package_name="test-package-2",
            version="2.0.0",
            repository="extra",
            installed_size=2048,
            dependencies=[]
        )
    ]
    
    # Create system state
    system_state = SystemState(
        endpoint_id=endpoint.id,
        timestamp=datetime.now(),
        packages=packages,
        pacman_version="6.0.1",
        architecture="x86_64"
    )
    
    # Test save state
    state_id = await orm.package_states.save_state(pool.id, endpoint.id, system_state)
    assert state_id is not None
    logger.info("✓ System state save successful")
    
    # Test get state
    retrieved_state = await orm.package_states.get_state(state_id)
    assert retrieved_state is not None
    assert retrieved_state.endpoint_id == endpoint.id
    assert len(retrieved_state.packages) == 2
    assert retrieved_state.packages[0].package_name == "test-package-1"
    logger.info("✓ System state retrieval successful")
    
    # Test set target state
    success = await orm.package_states.set_target_state(pool.id, state_id)
    assert success == True
    logger.info("✓ Target state setting successful")
    
    # Test get latest target state
    target_state = await orm.package_states.get_latest_target_state(pool.id)
    assert target_state is not None
    assert target_state.endpoint_id == endpoint.id
    logger.info("✓ Latest target state retrieval successful")
    
    # Test get endpoint states
    endpoint_states = await orm.package_states.get_endpoint_states(endpoint.id, limit=5)
    assert len(endpoint_states) >= 1
    logger.info("✓ Endpoint states listing successful")
    
    return state_id


async def test_sync_operation_operations(orm: ORMManager, pool: PackagePool, endpoint: Endpoint):
    """Test SyncOperation operations."""
    logger.info("Testing SyncOperation operations...")
    
    # Test create
    operation = SyncOperation(
        id="test-operation-1",
        pool_id=pool.id,
        endpoint_id=endpoint.id,
        operation_type=OperationType.SYNC,
        status=OperationStatus.PENDING,
        details={"test": "data"}
    )
    
    created_operation = await orm.sync_operations.create(operation)
    assert created_operation.operation_type == OperationType.SYNC
    assert created_operation.status == OperationStatus.PENDING
    logger.info("✓ Sync operation creation successful")
    
    # Test get by ID
    retrieved_operation = await orm.sync_operations.get_by_id("test-operation-1")
    assert retrieved_operation is not None
    assert retrieved_operation.pool_id == pool.id
    logger.info("✓ Sync operation retrieval successful")
    
    # Test update status
    success = await orm.sync_operations.update_status(
        "test-operation-1", 
        OperationStatus.COMPLETED
    )
    assert success == True
    
    # Verify status update
    retrieved_operation = await orm.sync_operations.get_by_id("test-operation-1")
    assert retrieved_operation.status == OperationStatus.COMPLETED
    assert retrieved_operation.completed_at is not None
    logger.info("✓ Sync operation status update successful")
    
    # Test list by endpoint
    endpoint_operations = await orm.sync_operations.list_by_endpoint(endpoint.id)
    assert len(endpoint_operations) >= 1
    logger.info("✓ Sync operation listing by endpoint successful")
    
    # Test list by pool
    pool_operations = await orm.sync_operations.list_by_pool(pool.id)
    assert len(pool_operations) >= 1
    logger.info("✓ Sync operation listing by pool successful")
    
    return created_operation


async def test_repository_operations(orm: ORMManager, endpoint: Endpoint):
    """Test Repository operations."""
    logger.info("Testing Repository operations...")
    
    # Create test packages
    packages = [
        RepositoryPackage(
            name="repo-package-1",
            version="1.0.0",
            repository="core",
            architecture="x86_64",
            description="Test package 1"
        ),
        RepositoryPackage(
            name="repo-package-2",
            version="2.0.0",
            repository="core",
            architecture="x86_64",
            description="Test package 2"
        )
    ]
    
    # Test create
    repository = Repository(
        id="test-repo-1",
        endpoint_id=endpoint.id,
        repo_name="core",
        repo_url="https://mirror.example.com/core",
        packages=packages
    )
    
    created_repository = await orm.repositories.create_or_update(repository)
    assert created_repository.repo_name == "core"
    assert len(created_repository.packages) == 2
    logger.info("✓ Repository creation successful")
    
    # Test get by endpoint and name
    retrieved_repository = await orm.repositories.get_by_endpoint_and_name(
        endpoint.id, "core"
    )
    assert retrieved_repository is not None
    assert retrieved_repository.repo_name == "core"
    logger.info("✓ Repository retrieval successful")
    
    # Test update (create_or_update with existing)
    updated_packages = packages + [
        RepositoryPackage(
            name="repo-package-3",
            version="3.0.0",
            repository="core",
            architecture="x86_64",
            description="Test package 3"
        )
    ]
    
    repository.packages = updated_packages
    updated_repository = await orm.repositories.create_or_update(repository)
    assert len(updated_repository.packages) == 3
    logger.info("✓ Repository update successful")
    
    # Test list by endpoint
    endpoint_repositories = await orm.repositories.list_by_endpoint(endpoint.id)
    assert len(endpoint_repositories) >= 1
    logger.info("✓ Repository listing by endpoint successful")
    
    return created_repository


async def test_validation_errors(orm: ORMManager):
    """Test validation error handling."""
    logger.info("Testing validation errors...")
    
    # Test empty pool name
    try:
        invalid_pool = PackagePool(
            id="invalid-pool",
            name="",  # Empty name
            description="Invalid pool"
        )
        await orm.pools.create(invalid_pool)
        assert False, "Should have raised ValueError"
    except ValueError:
        logger.info("✓ Empty pool name validation working")
    
    # Test empty endpoint name
    try:
        invalid_endpoint = Endpoint(
            id="invalid-endpoint",
            name="",  # Empty name
            hostname="test-host"
        )
        await orm.endpoints.create(invalid_endpoint)
        assert False, "Should have raised ValueError"
    except ValueError:
        logger.info("✓ Empty endpoint name validation working")
    
    # Test empty package name
    try:
        invalid_package = PackageState(
            package_name="",  # Empty name
            version="1.0.0",
            repository="core",
            installed_size=1024
        )
        # This should fail in the PackageState constructor
        assert False, "Should have raised ValueError"
    except ValueError:
        logger.info("✓ Empty package name validation working")


async def test_not_found_errors(orm: ORMManager):
    """Test not found error handling."""
    logger.info("Testing not found errors...")
    
    # Test get non-existent pool
    pool = await orm.pools.get_by_id("non-existent-pool")
    assert pool is None
    logger.info("✓ Non-existent pool returns None")
    
    # Test update non-existent pool
    try:
        await orm.pools.update("non-existent-pool", name="Updated")
        assert False, "Should have raised NotFoundError"
    except NotFoundError:
        logger.info("✓ Update non-existent pool raises NotFoundError")
    
    # Test delete non-existent endpoint
    success = await orm.endpoints.delete("non-existent-endpoint")
    assert success == False
    logger.info("✓ Delete non-existent endpoint returns False")


async def cleanup_test_data(orm: ORMManager):
    """Clean up test data."""
    logger.info("Cleaning up test data...")
    
    # Delete test entities
    await orm.pools.delete("test-pool-1")
    await orm.endpoints.delete("test-endpoint-1")
    
    logger.info("✓ Test data cleanup completed")


async def main():
    """Main test function."""
    logger.info("Starting ORM layer tests...")
    
    # Initialize database
    db_manager = DatabaseManager("internal")
    await db_manager.initialize()
    
    try:
        # Create fresh schema
        await drop_tables(db_manager)
        await create_tables(db_manager)
        
        # Initialize ORM
        orm = ORMManager(db_manager)
        
        # Run tests
        pool = await test_pool_operations(orm)
        endpoint = await test_endpoint_operations(orm, pool)
        state_id = await test_package_state_operations(orm, pool, endpoint)
        operation = await test_sync_operation_operations(orm, pool, endpoint)
        repository = await test_repository_operations(orm, endpoint)
        
        await test_validation_errors(orm)
        await test_not_found_errors(orm)
        
        await cleanup_test_data(orm)
        
        logger.info("🎉 All ORM tests passed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())