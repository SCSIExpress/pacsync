#!/usr/bin/env python3
"""
Test script for real pool assignment scenario using the main client.
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


async def test_real_pool_assignment():
    """Test real pool assignment scenario with token manager integration."""
    
    print("🧪 Testing Real Pool Assignment Scenario")
    print("=" * 50)
    
    # Initialize components
    server_url = "http://localhost:4444"
    endpoint_name = "test-real-pool-client"
    
    # Create config
    config = ClientConfiguration()
    
    # Create API client with config
    api_client = PacmanSyncAPIClient(server_url)
    api_client.token_manager.config = config
    
    try:
        # Step 1: Authenticate (this will initialize the token manager)
        print("\n1. Authenticating with server...")
        token = await api_client.authenticate(endpoint_name, "TestMachine")
        
        if not token:
            print("❌ Authentication failed")
            return False
        
        endpoint_id = api_client.token_manager.get_current_endpoint_id()
        print(f"✅ Authentication successful. Endpoint ID: {endpoint_id}")
        
        # Step 2: Simulate pool assignment by manually calling the pool assignment change
        print("\n2. Simulating pool assignment via token manager...")
        
        # This simulates what happens when the server assigns the endpoint to a pool
        # and the token manager detects the change during its periodic sync
        api_client.token_manager._notify_pool_assignment_change("test-real-pool", True)
        
        # Give it some time to complete the async sync
        print("   Waiting for automatic sync to complete...")
        await asyncio.sleep(5)  # Wait for the sync to complete
        
        print("✅ Pool assignment notification sent")
        
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
                        
                        # Calculate totals
                        total_packages = sum(len(repo.get('packages', [])) for repo in data['repositories'])
                        total_mirrors = sum(len(repo.get('mirrors', [])) for repo in data['repositories'])
                        
                        print(f"   Total packages: {total_packages}")
                        print(f"   Total mirrors: {total_mirrors}")
                        
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
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await api_client.close()


async def main():
    """Main test function."""
    success = await test_real_pool_assignment()
    
    if success:
        print("\n🎉 Real pool assignment test PASSED!")
        print("✅ Automatic sync on pool assignment is working correctly!")
        return 0
    else:
        print("\n💥 Real pool assignment test FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))