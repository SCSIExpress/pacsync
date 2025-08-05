#!/usr/bin/env python3
"""
Test script to verify the RepositoryAnalyzer implementation.
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


async def test_repository_analyzer():
    """Test the RepositoryAnalyzer functionality."""
    print("Testing RepositoryAnalyzer implementation...")
    
    # Initialize database manager (using SQLite for testing)
    db_manager = DatabaseManager(database_type="internal")
    await db_manager.initialize()
    
    # Run database migrations
    from server.database.migrations import run_migrations
    await run_migrations(db_manager)
    
    # Initialize repository analyzer
    analyzer = RepositoryAnalyzer(db_manager)
    
    # Create test pool
    pool_id = str(uuid4())
    pool = PackagePool(
        id=pool_id,
        name="test-pool",
        description="Test pool for repository analysis",
        sync_policy=SyncPolicy(exclude_packages=["excluded-package"])
    )
    await analyzer.pool_repository.create(pool)
    print(f"✓ Created test pool: {pool_id}")
    
    # Create test endpoints
    endpoint1_id = str(uuid4())
    endpoint2_id = str(uuid4())
    
    endpoint1 = Endpoint(
        id=endpoint1_id,
        name="endpoint1",
        hostname="host1.example.com",
        pool_id=pool_id,
        sync_status=SyncStatus.IN_SYNC
    )
    
    endpoint2 = Endpoint(
        id=endpoint2_id,
        name="endpoint2", 
        hostname="host2.example.com",
        pool_id=pool_id,
        sync_status=SyncStatus.IN_SYNC
    )
    
    await analyzer.endpoint_repository.create(endpoint1)
    await analyzer.endpoint_repository.create(endpoint2)
    print(f"✓ Created test endpoints: {endpoint1_id}, {endpoint2_id}")
    
    # Create test repository data
    # Endpoint 1 repositories
    repo1_core = Repository(
        id=str(uuid4()),
        endpoint_id=endpoint1_id,
        repo_name="core",
        repo_url="https://mirror.example.com/core",
        packages=[
            RepositoryPackage(name="common-package", version="1.0.0", repository="core", architecture="x86_64"),
            RepositoryPackage(name="endpoint1-only", version="2.0.0", repository="core", architecture="x86_64"),
            RepositoryPackage(name="version-conflict", version="1.0.0", repository="core", architecture="x86_64"),
            RepositoryPackage(name="excluded-package", version="1.0.0", repository="core", architecture="x86_64"),
        ]
    )
    
    repo1_extra = Repository(
        id=str(uuid4()),
        endpoint_id=endpoint1_id,
        repo_name="extra",
        repo_url="https://mirror.example.com/extra",
        packages=[
            RepositoryPackage(name="extra-common", version="3.0.0", repository="extra", architecture="x86_64"),
        ]
    )
    
    # Endpoint 2 repositories
    repo2_core = Repository(
        id=str(uuid4()),
        endpoint_id=endpoint2_id,
        repo_name="core",
        repo_url="https://mirror.example.com/core",
        packages=[
            RepositoryPackage(name="common-package", version="1.0.0", repository="core", architecture="x86_64"),
            RepositoryPackage(name="endpoint2-only", version="2.5.0", repository="core", architecture="x86_64"),
            RepositoryPackage(name="version-conflict", version="2.0.0", repository="core", architecture="x86_64"),
            RepositoryPackage(name="excluded-package", version="1.0.0", repository="core", architecture="x86_64"),
        ]
    )
    
    repo2_extra = Repository(
        id=str(uuid4()),
        endpoint_id=endpoint2_id,
        repo_name="extra",
        repo_url="https://mirror.example.com/extra",
        packages=[
            RepositoryPackage(name="extra-common", version="3.0.0", repository="extra", architecture="x86_64"),
        ]
    )
    
    # Update repository information
    repositories1 = [repo1_core, repo1_extra]
    repositories2 = [repo2_core, repo2_extra]
    
    success1 = await analyzer.update_repository_info(endpoint1_id, repositories1)
    success2 = await analyzer.update_repository_info(endpoint2_id, repositories2)
    
    print(f"✓ Updated repository info: endpoint1={success1}, endpoint2={success2}")
    
    # Test repository info retrieval
    retrieved_repos1 = await analyzer.get_repository_info(endpoint1_id)
    retrieved_repos2 = await analyzer.get_repository_info(endpoint2_id)
    
    print(f"✓ Retrieved repositories: endpoint1={len(retrieved_repos1)}, endpoint2={len(retrieved_repos2)}")
    
    # Test compatibility analysis
    analysis = await analyzer.analyze_pool_compatibility(pool_id)
    
    print(f"\n=== Compatibility Analysis Results ===")
    print(f"Pool ID: {analysis.pool_id}")
    print(f"Analysis time: {analysis.last_analyzed}")
    print(f"Common packages: {len(analysis.common_packages)}")
    print(f"Excluded packages: {len(analysis.excluded_packages)}")
    print(f"Conflicts: {len(analysis.conflicts)}")
    
    print(f"\nCommon packages:")
    for pkg in analysis.common_packages:
        print(f"  - {pkg.name} v{pkg.version} ({pkg.repository})")
    
    print(f"\nExcluded packages:")
    for pkg in analysis.excluded_packages:
        print(f"  - {pkg.name} v{pkg.version} ({pkg.repository}) - {pkg.description}")
    
    print(f"\nConflicts:")
    for conflict in analysis.conflicts:
        print(f"  - {conflict.package_name}: {conflict.endpoint_versions}")
        print(f"    Resolution: {conflict.suggested_resolution}")
    
    # Test package matrix
    matrix = await analyzer.get_pool_package_matrix(pool_id)
    print(f"\n=== Package Matrix ===")
    for package_name, endpoint_versions in matrix.items():
        print(f"{package_name}:")
        for endpoint_id, version in endpoint_versions.items():
            endpoint_name = "endpoint1" if endpoint_id == endpoint1_id else "endpoint2"
            version_str = version if version else "NOT AVAILABLE"
            print(f"  {endpoint_name}: {version_str}")
    
    # Test excluded packages retrieval
    excluded = await analyzer.get_excluded_packages_for_pool(pool_id)
    print(f"\n=== Excluded Packages for Pool ===")
    print(f"Total excluded: {len(excluded)}")
    
    # Verify expected results
    expected_common = ["common-package", "extra-common"]  # Available on both endpoints, same version
    expected_excluded = ["endpoint1-only", "endpoint2-only", "version-conflict", "excluded-package"]
    expected_conflicts = ["version-conflict"]  # Different versions on endpoints
    
    common_names = [pkg.name for pkg in analysis.common_packages]
    excluded_names = [pkg.name for pkg in analysis.excluded_packages]
    conflict_names = [conflict.package_name for conflict in analysis.conflicts]
    
    print(f"\n=== Verification ===")
    print(f"Expected common packages: {expected_common}")
    print(f"Actual common packages: {common_names}")
    print(f"Common packages match: {set(expected_common) == set(common_names)}")
    
    print(f"Expected excluded packages: {expected_excluded}")
    print(f"Actual excluded packages: {excluded_names}")
    print(f"Excluded packages match: {set(expected_excluded) == set(excluded_names)}")
    
    print(f"Expected conflicts: {expected_conflicts}")
    print(f"Actual conflicts: {conflict_names}")
    print(f"Conflicts match: {set(expected_conflicts) == set(conflict_names)}")
    
    # Cleanup
    await db_manager.close()
    
    # Remove test database
    import os
    if os.path.exists("test_repo_analyzer.db"):
        os.remove("test_repo_analyzer.db")
    
    print(f"\n✓ Repository analyzer test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_repository_analyzer())