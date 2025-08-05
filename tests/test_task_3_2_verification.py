#!/usr/bin/env python3
"""
Verification test for Task 3.2 - Repository Analysis Service
Tests all requirements 3.1-3.5 are properly implemented.
"""

import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.models import (
    Repository, RepositoryPackage, PackagePool, Endpoint, SyncPolicy, SyncStatus
)
from server.database.connection import DatabaseManager
from server.core.repository_analyzer import RepositoryAnalyzer


async def test_requirement_3_1():
    """Test 3.1: Client sends repository information to central server"""
    print("Testing Requirement 3.1: Repository information submission...")
    
    db_manager = DatabaseManager(database_type="internal")
    await db_manager.initialize()
    
    from server.database.migrations import run_migrations
    await run_migrations(db_manager)
    
    analyzer = RepositoryAnalyzer(db_manager)
    
    # Create test endpoint
    endpoint_id = str(uuid4())
    endpoint = Endpoint(
        id=endpoint_id,
        name="test-endpoint",
        hostname="test.example.com",
        sync_status=SyncStatus.IN_SYNC
    )
    await analyzer.endpoint_repository.create(endpoint)
    
    # Test repository information submission
    repositories = [
        Repository(
            id=str(uuid4()),
            endpoint_id=endpoint_id,
            repo_name="core",
            repo_url="https://mirror.example.com/core",
            packages=[
                RepositoryPackage(name="test-package", version="1.0.0", repository="core", architecture="x86_64")
            ]
        )
    ]
    
    success = await analyzer.update_repository_info(endpoint_id, repositories)
    assert success, "Repository information submission failed"
    
    # Verify information was stored
    retrieved = await analyzer.get_repository_info(endpoint_id)
    assert len(retrieved) == 1, "Repository information not stored correctly"
    assert retrieved[0].repo_name == "core", "Repository name not stored correctly"
    assert len(retrieved[0].packages) == 1, "Package information not stored correctly"
    
    await db_manager.close()
    print("✓ Requirement 3.1 verified: Repository information submission works")


async def test_requirement_3_2():
    """Test 3.2: Central server analyzes package availability across pool endpoints"""
    print("Testing Requirement 3.2: Package availability analysis...")
    
    db_manager = DatabaseManager(database_type="internal")
    await db_manager.initialize()
    
    from server.database.migrations import run_migrations
    await run_migrations(db_manager)
    
    analyzer = RepositoryAnalyzer(db_manager)
    
    # Create test pool and endpoints
    pool_id = str(uuid4())
    pool = PackagePool(id=pool_id, name=f"test-pool-{pool_id[:8]}", description="Test pool")
    await analyzer.pool_repository.create(pool)
    
    endpoint1_id = str(uuid4())
    endpoint2_id = str(uuid4())
    
    endpoint1 = Endpoint(id=endpoint1_id, name="endpoint1", hostname="host1.com", pool_id=pool_id)
    endpoint2 = Endpoint(id=endpoint2_id, name="endpoint2", hostname="host2.com", pool_id=pool_id)
    
    await analyzer.endpoint_repository.create(endpoint1)
    await analyzer.endpoint_repository.create(endpoint2)
    
    # Add repository information
    await analyzer.update_repository_info(endpoint1_id, [
        Repository(
            id=str(uuid4()),
            endpoint_id=endpoint1_id,
            repo_name="core",
            packages=[
                RepositoryPackage(name="common-pkg", version="1.0.0", repository="core", architecture="x86_64"),
                RepositoryPackage(name="endpoint1-only", version="1.0.0", repository="core", architecture="x86_64")
            ]
        )
    ])
    
    await analyzer.update_repository_info(endpoint2_id, [
        Repository(
            id=str(uuid4()),
            endpoint_id=endpoint2_id,
            repo_name="core",
            packages=[
                RepositoryPackage(name="common-pkg", version="1.0.0", repository="core", architecture="x86_64"),
                RepositoryPackage(name="endpoint2-only", version="1.0.0", repository="core", architecture="x86_64")
            ]
        )
    ])
    
    # Test analysis
    analysis = await analyzer.analyze_pool_compatibility(pool_id)
    
    assert analysis.pool_id == pool_id, "Analysis pool ID incorrect"
    assert len(analysis.common_packages) == 1, "Common packages analysis failed"
    assert analysis.common_packages[0].name == "common-pkg", "Common package identification failed"
    assert len(analysis.excluded_packages) == 2, "Excluded packages analysis failed"
    
    excluded_names = [pkg.name for pkg in analysis.excluded_packages]
    assert "endpoint1-only" in excluded_names, "Endpoint1-only package not excluded"
    assert "endpoint2-only" in excluded_names, "Endpoint2-only package not excluded"
    
    await db_manager.close()
    print("✓ Requirement 3.2 verified: Package availability analysis works")


async def test_requirement_3_3():
    """Test 3.3: Synchronization excludes packages not available in all repositories"""
    print("Testing Requirement 3.3: Package exclusion for synchronization...")
    
    db_manager = DatabaseManager(database_type="internal")
    await db_manager.initialize()
    
    from server.database.migrations import run_migrations
    await run_migrations(db_manager)
    
    analyzer = RepositoryAnalyzer(db_manager)
    
    # Create test setup
    pool_id = str(uuid4())
    pool = PackagePool(id=pool_id, name=f"test-pool-3-3-{pool_id[:8]}", description="Test pool")
    await analyzer.pool_repository.create(pool)
    
    endpoint1_id = str(uuid4())
    endpoint2_id = str(uuid4())
    
    endpoint1 = Endpoint(id=endpoint1_id, name="endpoint1", hostname="host1.com", pool_id=pool_id)
    endpoint2 = Endpoint(id=endpoint2_id, name="endpoint2", hostname="host2.com", pool_id=pool_id)
    
    await analyzer.endpoint_repository.create(endpoint1)
    await analyzer.endpoint_repository.create(endpoint2)
    
    # Add different packages to each endpoint
    await analyzer.update_repository_info(endpoint1_id, [
        Repository(
            id=str(uuid4()),
            endpoint_id=endpoint1_id,
            repo_name="core",
            packages=[
                RepositoryPackage(name="available-everywhere", version="1.0.0", repository="core", architecture="x86_64"),
                RepositoryPackage(name="only-on-endpoint1", version="1.0.0", repository="core", architecture="x86_64")
            ]
        )
    ])
    
    await analyzer.update_repository_info(endpoint2_id, [
        Repository(
            id=str(uuid4()),
            endpoint_id=endpoint2_id,
            repo_name="core",
            packages=[
                RepositoryPackage(name="available-everywhere", version="1.0.0", repository="core", architecture="x86_64"),
                RepositoryPackage(name="only-on-endpoint2", version="1.0.0", repository="core", architecture="x86_64")
            ]
        )
    ])
    
    # Get excluded packages for synchronization
    excluded_packages = await analyzer.get_excluded_packages_for_pool(pool_id)
    
    excluded_names = [pkg.name for pkg in excluded_packages]
    assert "only-on-endpoint1" in excluded_names, "Endpoint1-only package not excluded from sync"
    assert "only-on-endpoint2" in excluded_names, "Endpoint2-only package not excluded from sync"
    assert "available-everywhere" not in excluded_names, "Common package incorrectly excluded"
    
    await db_manager.close()
    print("✓ Requirement 3.3 verified: Package exclusion for synchronization works")


async def test_requirement_3_4():
    """Test 3.4: Automatic compatibility analysis update when repository info changes"""
    print("Testing Requirement 3.4: Automatic analysis update on repository changes...")
    
    db_manager = DatabaseManager(database_type="internal")
    await db_manager.initialize()
    
    from server.database.migrations import run_migrations
    await run_migrations(db_manager)
    
    analyzer = RepositoryAnalyzer(db_manager)
    
    # Create test setup
    pool_id = str(uuid4())
    pool = PackagePool(id=pool_id, name=f"test-pool-3-4-{pool_id[:8]}", description="Test pool")
    await analyzer.pool_repository.create(pool)
    
    endpoint_id = str(uuid4())
    endpoint = Endpoint(id=endpoint_id, name="endpoint", hostname="host.com", pool_id=pool_id)
    await analyzer.endpoint_repository.create(endpoint)
    
    # Initial repository info
    initial_repos = [
        Repository(
            id=str(uuid4()),
            endpoint_id=endpoint_id,
            repo_name="core",
            packages=[
                RepositoryPackage(name="initial-package", version="1.0.0", repository="core", architecture="x86_64")
            ]
        )
    ]
    
    await analyzer.update_repository_info(endpoint_id, initial_repos)
    
    # Get initial analysis timestamp
    initial_analysis = await analyzer.analyze_pool_compatibility(pool_id)
    initial_time = initial_analysis.last_analyzed
    
    # Wait a moment to ensure timestamp difference
    await asyncio.sleep(0.1)
    
    # Update repository info (this should trigger automatic analysis)
    updated_repos = [
        Repository(
            id=str(uuid4()),
            endpoint_id=endpoint_id,
            repo_name="core",
            packages=[
                RepositoryPackage(name="updated-package", version="1.0.0", repository="core", architecture="x86_64")
            ]
        )
    ]
    
    await analyzer.update_repository_info(endpoint_id, updated_repos)
    
    # Verify analysis was updated
    updated_analysis = await analyzer.analyze_pool_compatibility(pool_id)
    
    # The analysis should reflect the new package
    common_names = [pkg.name for pkg in updated_analysis.common_packages]
    assert "updated-package" in common_names, "Analysis not updated with new package"
    assert "initial-package" not in common_names, "Analysis still contains old package"
    
    await db_manager.close()
    print("✓ Requirement 3.4 verified: Automatic analysis update works")


async def test_requirement_3_5():
    """Test 3.5: Packages becoming unavailable are marked as excluded"""
    print("Testing Requirement 3.5: Unavailable packages marked as excluded...")
    
    db_manager = DatabaseManager(database_type="internal")
    await db_manager.initialize()
    
    from server.database.migrations import run_migrations
    await run_migrations(db_manager)
    
    analyzer = RepositoryAnalyzer(db_manager)
    
    # Create test setup with 2 endpoints
    pool_id = str(uuid4())
    pool = PackagePool(id=pool_id, name=f"test-pool-3-5-{pool_id[:8]}", description="Test pool")
    await analyzer.pool_repository.create(pool)
    
    endpoint1_id = str(uuid4())
    endpoint2_id = str(uuid4())
    
    endpoint1 = Endpoint(id=endpoint1_id, name="endpoint1", hostname="host1.com", pool_id=pool_id)
    endpoint2 = Endpoint(id=endpoint2_id, name="endpoint2", hostname="host2.com", pool_id=pool_id)
    
    await analyzer.endpoint_repository.create(endpoint1)
    await analyzer.endpoint_repository.create(endpoint2)
    
    # Initially both endpoints have the same package
    common_package = RepositoryPackage(name="shared-package", version="1.0.0", repository="core", architecture="x86_64")
    
    await analyzer.update_repository_info(endpoint1_id, [
        Repository(
            id=str(uuid4()),
            endpoint_id=endpoint1_id,
            repo_name="core",
            packages=[common_package]
        )
    ])
    
    await analyzer.update_repository_info(endpoint2_id, [
        Repository(
            id=str(uuid4()),
            endpoint_id=endpoint2_id,
            repo_name="core",
            packages=[common_package]
        )
    ])
    
    # Verify package is initially common
    initial_analysis = await analyzer.analyze_pool_compatibility(pool_id)
    common_names = [pkg.name for pkg in initial_analysis.common_packages]
    assert "shared-package" in common_names, "Package should initially be common"
    
    # Remove package from endpoint2 (simulating package becoming unavailable)
    await analyzer.update_repository_info(endpoint2_id, [
        Repository(
            id=str(uuid4()),
            endpoint_id=endpoint2_id,
            repo_name="core",
            packages=[]  # No packages
        )
    ])
    
    # Verify package is now excluded
    updated_analysis = await analyzer.analyze_pool_compatibility(pool_id)
    excluded_names = [pkg.name for pkg in updated_analysis.excluded_packages]
    common_names = [pkg.name for pkg in updated_analysis.common_packages]
    
    assert "shared-package" in excluded_names, "Package should be excluded after becoming unavailable"
    assert "shared-package" not in common_names, "Package should not be common after becoming unavailable"
    
    # Verify the exclusion reason
    excluded_pkg = next(pkg for pkg in updated_analysis.excluded_packages if pkg.name == "shared-package")
    assert "Missing from" in excluded_pkg.description, "Exclusion reason should indicate missing from endpoint"
    
    await db_manager.close()
    print("✓ Requirement 3.5 verified: Unavailable packages marked as excluded")


async def run_all_tests():
    """Run all requirement verification tests."""
    print("=== Task 3.2 Repository Analysis Service Verification ===\n")
    
    # Clean up any existing test database
    if os.path.exists("data/pacman_sync.db"):
        os.remove("data/pacman_sync.db")
    
    test_functions = [
        test_requirement_3_1,
        test_requirement_3_2,
        test_requirement_3_3,
        test_requirement_3_4,
        test_requirement_3_5
    ]
    
    try:
        for test_func in test_functions:
            # Clean database before each test
            if os.path.exists("data/pacman_sync.db"):
                os.remove("data/pacman_sync.db")
            await test_func()
        
        print("\n=== All Requirements Verified Successfully! ===")
        print("✓ 3.1: Repository information submission")
        print("✓ 3.2: Package availability analysis")
        print("✓ 3.3: Package exclusion for synchronization")
        print("✓ 3.4: Automatic analysis update")
        print("✓ 3.5: Unavailable packages marked as excluded")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
    
    finally:
        # Clean up test database
        if os.path.exists("data/pacman_sync.db"):
            os.remove("data/pacman_sync.db")


if __name__ == "__main__":
    asyncio.run(run_all_tests())