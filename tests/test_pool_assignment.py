#!/usr/bin/env python3
"""
Test script for pool assignment automatic sync functionality.
"""

import asyncio
import logging
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.api_client import PacmanSyncAPIClient
from client.pool_assignment_handler import PoolAssignmentHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_pool_assignment_sync():
    """Test the pool assignment automatic sync functionality."""
    
    print("🧪 Testing Pool Assignment Automatic Sync")
    print("=" * 50)
    
    # Initialize components
    server_url = "http://localhost:4444"
    endpoint_name = "test-pool-assignment"
    
    api_client = PacmanSyncAPIClient(server_url)
    pool_handler = PoolAssignmentHandler(server_url, endpoint_name)
    
    try:
        # Step 1: Authenticate
        print("\n1. Authenticating with server...")
        token = await api_client.authenticate(endpoint_name, "TestMachine")
        
        if not token:
            print("❌ Authentication failed")
            return False
        
        endpoint_id = api_client.token_manager.get_current_endpoint_id()
        print(f"✅ Authentication successful. Endpoint ID: {endpoint_id}")
        
        # Step 2: Simulate pool assignment
        print("\n2. Simulating pool assignment...")
        
        # This would normally be called by the token manager when it detects a pool assignment
        await pool_handler.handle_pool_assignment_change(
            pool_id="test-pool-sync",
            assigned=True,
            api_client=api_client,
            endpoint_id=endpoint_id
        )
        
        print("✅ Pool assignment sync completed")
        
        # Step 3: Verify data was submitted
        print("\n3. Verifying repository data was submitted...")
        
        # Check if repositories were submitted
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server_url}/api/repositories/endpoint/{endpoint_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    repo_count = len(data.get('repositories', []))
                    
                    if repo_count > 0:
                        print(f"✅ Found {repo_count} repositories in server")
                        
                        # Show some details
                        for repo in data['repositories'][:3]:  # Show first 3
                            package_count = len(repo.get('packages', []))
                            mirror_count = len(repo.get('mirrors', []))
                            print(f"   - {repo['repo_name']}: {package_count} packages, {mirror_count} mirrors")
                        
                        return True
                    else:
                        print("❌ No repositories found in server")
                        return False
                else:
                    print(f"❌ Failed to retrieve repository data: {response.status}")
                    return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
        
    finally:
        await api_client.close()


async def main():
    """Main test function."""
    success = await test_pool_assignment_sync()
    
    if success:
        print("\n🎉 Pool assignment automatic sync test PASSED!")
        return 0
    else:
        print("\n💥 Pool assignment automatic sync test FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))