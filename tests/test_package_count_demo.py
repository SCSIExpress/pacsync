#!/usr/bin/env python3
"""
Demo of package counting functionality with real data.

This script demonstrates:
1. Creating endpoints with package data
2. Setting up a pool with target state
3. Counting packages in the target state
4. Showing sync status for endpoints
"""

import asyncio
import logging
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.api_client import PacmanSyncAPIClient
from client.repository_sync_client import RepositorySyncClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_package_counting():
    """Demonstrate package counting functionality."""
    
    print("🎯 Package Counting Demo")
    print("=" * 40)
    
    server_url = "http://localhost:4444"
    
    # Step 1: Create an endpoint with full package data
    print("\n📋 Step 1: Creating endpoint with package data")
    print("-" * 50)
    
    endpoint_name = "package-count-demo"
    
    api_client = PacmanSyncAPIClient(server_url)
    token = await api_client.authenticate(endpoint_name, "DemoMachine")
    
    if not token:
        print("❌ Authentication failed")
        return False
    
    endpoint_id = api_client.token_manager.get_current_endpoint_id()
    print(f"✅ Created endpoint: {endpoint_name}")
    print(f"   Endpoint ID: {endpoint_id}")
    
    # Submit full repository data
    sync_client = RepositorySyncClient(server_url, endpoint_name)
    success = await sync_client.perform_pool_assignment_sync(api_client, endpoint_id)
    
    if not success:
        print("❌ Failed to submit repository data")
        return False
    
    print("✅ Repository data submitted (23,380+ packages)")
    
    # Step 2: Create pool and assign endpoint first
    print("\n📋 Step 2: Creating pool and assigning endpoint")
    print("-" * 48)
    
    import aiohttp
    
    # Create pool with unique name
    import time
    pool_data = {
        "name": f"Package Count Demo Pool {int(time.time())}",
        "description": "Demo pool for package counting functionality"
    }
    
    async with aiohttp.ClientSession() as session:
        # Create pool
        async with session.post(f"{server_url}/api/pools", json=pool_data) as response:
            if response.status == 201:
                pool_info = await response.json()
                pool_id = pool_info['id']
                print(f"✅ Created pool: {pool_id}")
            else:
                print(f"❌ Failed to create pool: {response.status}")
                return False
        
        # Assign endpoint to pool
        headers = {'Authorization': f'Bearer {token}'}
        async with session.put(
            f"{server_url}/api/endpoints/{endpoint_id}/pool?pool_id={pool_id}",
            headers=headers
        ) as response:
            if response.status == 200:
                print(f"✅ Assigned endpoint to pool")
            else:
                error_text = await response.text()
                print(f"❌ Failed to assign endpoint to pool: {response.status} - {error_text}")
                return False
    
    # Step 3: Submit system state (now that endpoint is in a pool)
    print("\n📋 Step 3: Submitting system state")
    print("-" * 38)
    
    # Get current system state
    from client.pacman_interface import PacmanInterface
    pacman = PacmanInterface()
    system_state = pacman.get_system_state(endpoint_id)
    
    # Submit state
    state_id = await api_client.submit_state(endpoint_id, system_state)
    print(f"✅ System state submitted")
    print(f"   State ID: {state_id}")
    print(f"   Installed packages: {len(system_state.packages)}")
    
    # Step 4: Set target state for pool
    print("\n📋 Step 4: Setting target state for pool")
    print("-" * 42)
    
    async with aiohttp.ClientSession() as session:
        # Set target state for pool using pool update endpoint
        update_data = {"target_state_id": state_id}
        async with session.put(
            f"{server_url}/api/pools/{pool_id}",
            json=update_data
        ) as response:
            if response.status == 200:
                print(f"✅ Set target state for pool")
            else:
                error_text = await response.text()
                print(f"❌ Failed to set target state: {response.status} - {error_text}")
                return False
    
    # Step 5: Test package counting
    print("\n📋 Step 5: Testing package counting")
    print("-" * 38)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{server_url}/api/package-sync/pools/{pool_id}/package-count"
        ) as response:
            if response.status == 200:
                count_data = await response.json()
                print(f"✅ Package count results:")
                print(f"   Pool ID: {count_data['pool_id']}")
                print(f"   Target state ID: {count_data['target_state_id']}")
                print(f"   Total packages: {count_data['total_packages']}")
                print(f"   Architecture: {count_data['architecture']}")
                print(f"   Last updated: {count_data['last_updated']}")
                
                if count_data['packages_by_repository']:
                    print(f"   📦 Packages by repository:")
                    total_shown = 0
                    for repo, count in count_data['packages_by_repository'].items():
                        print(f"     {repo}: {count:,} packages")
                        total_shown += count
                    print(f"   📊 Total: {total_shown:,} packages")
                
            else:
                error_text = await response.text()
                print(f"❌ Failed to get package count: {response.status} - {error_text}")
                return False
    
    # Step 6: Test endpoint sync status
    print("\n📋 Step 6: Testing endpoint sync status")
    print("-" * 42)
    
    headers = {'Authorization': f'Bearer {token}'}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{server_url}/api/package-sync/endpoints/{endpoint_id}/sync-status",
            headers=headers
        ) as response:
            if response.status == 200:
                status_data = await response.json()
                print(f"✅ Endpoint sync status:")
                print(f"   Endpoint ID: {status_data['endpoint_id']}")
                print(f"   Pool ID: {status_data['pool_id']}")
                print(f"   Sync status: {status_data['sync_status']}")
                print(f"   Target packages: {status_data['target_packages']:,}")
                print(f"   Current packages: {status_data['current_packages']:,}")
                print(f"   📥 To install: {status_data['packages_to_install']:,}")
                print(f"   📤 To upgrade: {status_data['packages_to_upgrade']:,}")
                print(f"   🗑️  To remove: {status_data['packages_to_remove']:,}")
                print(f"   Last sync: {status_data['last_sync']}")
            else:
                error_text = await response.text()
                print(f"❌ Failed to get sync status: {response.status} - {error_text}")
                return False
    
    # Step 7: Test pool sync summary
    print("\n📋 Step 7: Testing pool sync summary")
    print("-" * 38)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{server_url}/api/package-sync/pools/{pool_id}/endpoints/sync-summary"
        ) as response:
            if response.status == 200:
                summary_data = await response.json()
                print(f"✅ Pool sync summary:")
                print(f"   Pool ID: {summary_data['pool_id']}")
                print(f"   Total endpoints: {summary_data['total_endpoints']}")
                print(f"   Target packages: {summary_data['target_packages']:,}")
                
                if summary_data['sync_status_counts']:
                    print(f"   📊 Sync status distribution:")
                    for status, count in summary_data['sync_status_counts'].items():
                        print(f"     {status}: {count} endpoint(s)")
            else:
                error_text = await response.text()
                print(f"❌ Failed to get pool sync summary: {response.status} - {error_text}")
                return False
    
    # Cleanup
    await api_client.close()
    
    return True


async def main():
    """Main demo function."""
    success = await demo_package_counting()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 PACKAGE COUNTING DEMO COMPLETED!")
        print("✅ All package sync features demonstrated successfully!")
        print("\n📋 Features demonstrated:")
        print("   1. ✅ Package counting in target states")
        print("   2. ✅ Packages by repository breakdown")
        print("   3. ✅ Endpoint sync status analysis")
        print("   4. ✅ Pool sync summaries")
        print("   5. ✅ Real package data (23,000+ packages)")
        return 0
    else:
        print("💥 PACKAGE COUNTING DEMO FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))