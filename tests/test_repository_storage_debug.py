#!/usr/bin/env python3
"""
Debug script for repository storage issues.

This script tests if repository data is being stored correctly in the database.
"""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

SERVER_URL = "http://localhost:4444"


async def test_direct_database_query():
    """Test direct database query to see if repository data exists."""
    print("🔍 Testing direct database access...")
    
    try:
        # Import server components
        from server.database.connection import DatabaseManager
        from server.database.orm import RepositoryRepository
        
        # Create database connection
        db_manager = DatabaseManager(database_type="internal")
        await db_manager.initialize()
        
        # Create repository ORM
        repo_repository = RepositoryRepository(db_manager)
        
        # Query all repositories
        print("📦 Querying all repositories in database...")
        
        # Use raw SQL to check what's in the database
        if db_manager.database_type == "postgresql":
            query = "SELECT id, endpoint_id, repo_name, repo_url, mirrors, packages FROM repositories LIMIT 10"
        else:
            query = "SELECT id, endpoint_id, repo_name, repo_url, mirrors, packages FROM repositories LIMIT 10"
        
        rows = await db_manager.fetch(query)
        
        print(f"✅ Found {len(rows)} repositories in database:")
        
        for i, row in enumerate(rows, 1):
            print(f"   {i}. ID: {row[0]}")
            print(f"      Endpoint: {row[1]}")
            print(f"      Name: {row[2]}")
            print(f"      URL: {row[3]}")
            print(f"      Mirrors: {row[4]}")
            print(f"      Packages: {len(json.loads(row[5]) if row[5] else [])}")
            print()
        
        await db_manager.close()
        return len(rows) > 0
        
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_repository_orm():
    """Test the repository ORM directly."""
    print("\n🔧 Testing repository ORM...")
    
    try:
        # Import server components
        from server.database.connection import DatabaseManager
        from server.database.orm import RepositoryRepository
        from shared.models import Repository
        from datetime import datetime
        
        # Create database connection
        db_manager = DatabaseManager(database_type="internal")
        await db_manager.initialize()
        
        # Create repository ORM
        repo_repository = RepositoryRepository(db_manager)
        
        # Create a test repository
        test_repo = Repository(
            id="test-repo-debug",
            endpoint_id="test-endpoint-debug",
            repo_name="test-repo",
            repo_url="http://test.example.com/repo",
            mirrors=["http://mirror1.example.com", "http://mirror2.example.com"],
            packages=[],
            last_updated=datetime.now()
        )
        
        print(f"📝 Creating test repository: {test_repo.repo_name}")
        
        # Store the repository
        stored_repo = await repo_repository.create_or_update(test_repo)
        
        if stored_repo:
            print(f"✅ Repository stored successfully: {stored_repo.id}")
            print(f"   Name: {stored_repo.repo_name}")
            print(f"   URL: {stored_repo.repo_url}")
            print(f"   Mirrors: {stored_repo.mirrors}")
            
            # Try to retrieve it
            print(f"🔍 Retrieving repository by endpoint...")
            repos = await repo_repository.list_by_endpoint("test-endpoint-debug")
            
            print(f"✅ Retrieved {len(repos)} repositories for test endpoint")
            
            for repo in repos:
                print(f"   - {repo.repo_name}: {repo.repo_url}")
                print(f"     Mirrors: {repo.mirrors}")
            
            # Clean up
            print(f"🧹 Cleaning up test data...")
            await repo_repository.delete_by_endpoint("test-endpoint-debug")
            
            await db_manager.close()
            return True
        else:
            print(f"❌ Failed to store repository")
            await db_manager.close()
            return False
        
    except Exception as e:
        print(f"❌ Error testing repository ORM: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_endpoint_manager_repository_update():
    """Test the endpoint manager's repository update method."""
    print("\n🔄 Testing endpoint manager repository update...")
    
    try:
        # Import server components
        from server.database.connection import DatabaseManager
        from server.database.orm import ORMManager
        from server.core.endpoint_manager import EndpointManager
        from shared.models import Repository, Endpoint, SyncStatus
        from datetime import datetime
        
        # Create database connection
        db_manager = DatabaseManager(database_type="internal")
        await db_manager.initialize()
        
        # Create ORM manager
        orm = ORMManager(db_manager)
        
        # Create endpoint manager
        endpoint_manager = EndpointManager(orm)
        
        # Create a test endpoint first
        test_endpoint = Endpoint(
            id="test-endpoint-manager",
            name="Test Endpoint Manager",
            hostname="test-host",
            sync_status=SyncStatus.OFFLINE
        )
        
        print(f"📝 Creating test endpoint: {test_endpoint.name}")
        stored_endpoint = await orm.endpoints.create_or_update(test_endpoint)
        
        if not stored_endpoint:
            print(f"❌ Failed to create test endpoint")
            await db_manager.close()
            return False
        
        # Create test repositories
        test_repos = [
            Repository(
                id="",  # Will be generated
                endpoint_id="test-endpoint-manager",
                repo_name="core",
                repo_url="http://test.example.com/core",
                mirrors=["http://mirror1.example.com/core", "http://mirror2.example.com/core"],
                packages=[]
            ),
            Repository(
                id="",  # Will be generated
                endpoint_id="test-endpoint-manager",
                repo_name="extra",
                repo_url="http://test.example.com/extra",
                mirrors=["http://mirror1.example.com/extra"],
                packages=[]
            )
        ]
        
        print(f"📝 Updating repository info via endpoint manager...")
        success = await endpoint_manager.update_repository_info("test-endpoint-manager", test_repos)
        
        if success:
            print(f"✅ Repository update successful")
            
            # Verify the repositories were stored
            print(f"🔍 Verifying stored repositories...")
            stored_repos = await orm.repositories.list_by_endpoint("test-endpoint-manager")
            
            print(f"✅ Found {len(stored_repos)} stored repositories:")
            for repo in stored_repos:
                print(f"   - {repo.repo_name}: {repo.repo_url}")
                print(f"     Mirrors: {repo.mirrors}")
            
            # Clean up
            print(f"🧹 Cleaning up test data...")
            await orm.repositories.delete_by_endpoint("test-endpoint-manager")
            await orm.endpoints.delete("test-endpoint-manager")
            
            await db_manager.close()
            return len(stored_repos) == 2
        else:
            print(f"❌ Repository update failed")
            await db_manager.close()
            return False
        
    except Exception as e:
        print(f"❌ Error testing endpoint manager: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all repository storage debug tests."""
    print("🐛 Repository Storage Debug")
    print("=" * 35)
    
    # Test direct database query
    db_has_data = await test_direct_database_query()
    
    # Test repository ORM
    orm_works = await test_repository_orm()
    
    # Test endpoint manager
    manager_works = await test_endpoint_manager_repository_update()
    
    print("\n📋 Summary:")
    print(f"   Database has repository data: {'✅' if db_has_data else '❌'}")
    print(f"   Repository ORM works: {'✅' if orm_works else '❌'}")
    print(f"   Endpoint manager works: {'✅' if manager_works else '❌'}")
    
    if not db_has_data:
        print("\n💡 Possible issues:")
        print("   1. Repository data is not being stored")
        print("   2. Database schema is missing mirrors column")
        print("   3. Repository submission API is not working")
    
    if not orm_works:
        print("\n💡 Repository ORM issues:")
        print("   1. Database schema mismatch")
        print("   2. ORM serialization problems")
        print("   3. Database connection issues")
    
    if not manager_works:
        print("\n💡 Endpoint manager issues:")
        print("   1. Repository creation/update logic problems")
        print("   2. Transaction handling issues")
        print("   3. Data validation problems")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))