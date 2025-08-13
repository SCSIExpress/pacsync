#!/usr/bin/env python3
"""
Simple test for package sync functionality using existing data.
"""

import asyncio
import logging
import sys
import os
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_package_sync_endpoints():
    """Test the package sync endpoints with existing data."""
    
    print("🧪 Testing Package Sync Endpoints")
    print("=" * 50)
    
    server_url = "http://localhost:4444"
    
    import aiohttp
    
    # Step 1: Check if we have any pools
    print("\n📋 Step 1: Checking existing pools")
    print("-" * 35)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{server_url}/api/pools") as response:
            if response.status == 200:
                pools = await response.json()
                
                if pools:
                    pool = pools[0]  # Use first pool
                    pool_id = pool['id']
                    print(f"✅ Found pool: {pool['name']} (ID: {pool_id})")
                    
                    # Step 2: Test package count endpoint
                    print(f"\n📋 Step 2: Testing package count for pool {pool_id}")
                    print("-" * 55)
                    
                    async with session.get(f"{server_url}/api/package-sync/pools/{pool_id}/package-count") as response:
                        if response.status == 200:
                            count_data = await response.json()
                            print(f"✅ Package count retrieved:")
                            print(f"   Pool ID: {count_data['pool_id']}")
                            print(f"   Target state ID: {count_data['target_state_id']}")
                            print(f"   Total packages: {count_data['total_packages']}")
                            print(f"   Architecture: {count_data['architecture']}")
                            
                            if count_data['packages_by_repository']:
                                print(f"   Packages by repository:")
                                for repo, count in count_data['packages_by_repository'].items():
                                    print(f"     {repo}: {count} packages")
                            else:
                                print("   No target state set for this pool")
                        else:
                            error_text = await response.text()
                            print(f"❌ Failed to get package count: {response.status} - {error_text}")
                    
                    # Step 3: Test pool sync summary
                    print(f"\n📋 Step 3: Testing pool sync summary")
                    print("-" * 40)
                    
                    async with session.get(f"{server_url}/api/package-sync/pools/{pool_id}/endpoints/sync-summary") as response:
                        if response.status == 200:
                            summary_data = await response.json()
                            print(f"✅ Pool sync summary:")
                            print(f"   Pool ID: {summary_data['pool_id']}")
                            print(f"   Total endpoints: {summary_data['total_endpoints']}")
                            print(f"   Target packages: {summary_data['target_packages']}")
                            
                            if summary_data['sync_status_counts']:
                                print(f"   Sync status counts:")
                                for status, count in summary_data['sync_status_counts'].items():
                                    print(f"     {status}: {count} endpoints")
                            
                            if summary_data['endpoints']:
                                print(f"   Endpoints in pool:")
                                for endpoint in summary_data['endpoints'][:3]:  # Show first 3
                                    print(f"     - {endpoint['name']} ({endpoint['sync_status']})")
                        else:
                            error_text = await response.text()
                            print(f"❌ Failed to get pool sync summary: {response.status} - {error_text}")
                    
                    return True
                else:
                    print("❌ No pools found")
                    return False
            else:
                print(f"❌ Failed to get pools: {response.status}")
                return False


async def test_health_endpoint():
    """Test the health endpoint."""
    
    print("\n📋 Testing Health Endpoint")
    print("-" * 30)
    
    server_url = "http://localhost:4444"
    
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{server_url}/api/package-sync/health") as response:
            if response.status == 200:
                health_data = await response.json()
                print(f"✅ Health check passed:")
                print(f"   Status: {health_data['status']}")
                print(f"   Service: {health_data['service']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status}")
                return False


async def main():
    """Main test function."""
    
    print("🧪 Simple Package Sync API Test")
    print("=" * 40)
    
    # Test health endpoint first
    health_ok = await test_health_endpoint()
    
    if not health_ok:
        print("\n💥 Health check failed - server may not be running")
        return 1
    
    # Test package sync endpoints
    endpoints_ok = await test_package_sync_endpoints()
    
    print("\n" + "=" * 50)
    if health_ok and endpoints_ok:
        print("🎉 PACKAGE SYNC API TEST PASSED!")
        print("✅ All package sync endpoints are working!")
        return 0
    else:
        print("💥 PACKAGE SYNC API TEST FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))