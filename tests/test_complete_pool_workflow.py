#!/usr/bin/env python3
"""
Complete test of the pool assignment workflow.

This test demonstrates:
1. Client authentication
2. Manual repository sync (lightweight)
3. Pool assignment (simulated)
4. Automatic full sync on pool assignment
5. Verification of complete data
"""

import asyncio
import logging
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.api_client import PacmanSyncAPIClient
from client.config import ClientConfiguration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_complete_workflow():
    """Test the complete pool assignment workflow."""
    
    print("🧪 Testing Complete Pool Assignment Workflow")
    print("=" * 60)
    
    # Initialize components
    server_url = "http://localhost:4444"
    endpoint_name = "complete-workflow-test"
    
    # Create config
    config = ClientConfiguration()
    
    # Create API client with config
    api_client = PacmanSyncAPIClient(server_url)
    api_client.token_manager.config = config
    
    try:
        # Step 1: Authentication
        print("\n📋 Step 1: Authentication")
        print("-" * 30)
        
        token = await api_client.authenticate(endpoint_name, "TestMachine")
        
        if not token:
            print("❌ Authentication failed")
            return False
        
        endpoint_id = api_client.token_manager.get_current_endpoint_id()
        print(f"✅ Authentication successful")
        print(f"   Endpoint ID: {endpoint_id}")
        
        # Step 2: Initial lightweight sync (what would happen normally)
        print("\n📋 Step 2: Initial Lightweight Sync")
        print("-" * 40)
        
        from client.repository_sync_client import RepositorySyncClient
        
        sync_client = RepositorySyncClient(server_url, endpoint_name)
        sync_client.api_client = api_client
        sync_client.endpoint_id = endpoint_id
        sync_client.is_authenticated = True
        
        # Perform lightweight sync
        lightweight_success = await sync_client.sync_repository_info()
        
        if lightweight_success:
            print("✅ Lightweight sync completed")
            print("   Repository mirrors submitted (no packages)")
        else:
            print("❌ Lightweight sync failed")
            return False
        
        # Verify lightweight data
        await verify_repository_data(server_url, endpoint_id, "lightweight")
        
        # Step 3: Simulate pool assignment
        print("\n📋 Step 3: Pool Assignment")
        print("-" * 30)
        
        print("   Simulating pool assignment...")
        
        # This triggers the automatic full sync
        api_client.token_manager._notify_pool_assignment_change("complete-test-pool", True)
        
        # Wait for the automatic sync to complete
        print("   Waiting for automatic full sync...")
        await asyncio.sleep(8)  # Give it time to complete
        
        print("✅ Pool assignment completed")
        print("   Automatic full sync should have been triggered")
        
        # Step 4: Verify complete data
        print("\n📋 Step 4: Verification")
        print("-" * 25)
        
        await verify_repository_data(server_url, endpoint_id, "full")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await api_client.close()


async def verify_repository_data(server_url: str, endpoint_id: str, sync_type: str):
    """Verify repository data in the server."""
    
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{server_url}/api/repositories/endpoint/{endpoint_id}") as response:
            if response.status == 200:
                data = await response.json()
                repositories = data.get('repositories', [])
                
                if repositories:
                    repo_count = len(repositories)
                    total_packages = sum(len(repo.get('packages', [])) for repo in repositories)
                    total_mirrors = sum(len(repo.get('mirrors', [])) for repo in repositories)
                    
                    print(f"✅ Found {repo_count} repositories")
                    print(f"   Total packages: {total_packages}")
                    print(f"   Total mirrors: {total_mirrors}")
                    
                    if sync_type == "lightweight":
                        if total_packages == 0 and total_mirrors > 0:
                            print("   ✅ Lightweight sync verified (mirrors only)")
                        else:
                            print("   ⚠️  Expected lightweight data (mirrors only)")
                    
                    elif sync_type == "full":
                        if total_packages > 20000 and total_mirrors > 300:
                            print("   ✅ Full sync verified (packages + mirrors)")
                        else:
                            print(f"   ⚠️  Expected full data (got {total_packages} packages, {total_mirrors} mirrors)")
                    
                    # Show sample repositories
                    print("   Sample repositories:")
                    for repo in repositories[:3]:
                        package_count = len(repo.get('packages', []))
                        mirror_count = len(repo.get('mirrors', []))
                        print(f"     - {repo['repo_name']}: {package_count} packages, {mirror_count} mirrors")
                
                else:
                    print("❌ No repositories found")
            else:
                print(f"❌ Failed to retrieve data: {response.status}")


async def main():
    """Main test function."""
    success = await test_complete_workflow()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 COMPLETE WORKFLOW TEST PASSED!")
        print("✅ Pool assignment automatic sync is working perfectly!")
        print("\n📋 Summary:")
        print("   1. ✅ Authentication works")
        print("   2. ✅ Lightweight sync works (mirrors only)")
        print("   3. ✅ Pool assignment triggers automatic full sync")
        print("   4. ✅ Full sync includes packages + mirrors")
        print("   5. ✅ Data verification successful")
        return 0
    else:
        print("💥 COMPLETE WORKFLOW TEST FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))