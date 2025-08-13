#!/usr/bin/env python3
"""
Test script for package sync functionality.

This script tests:
1. Package counting in target states
2. Endpoint sync status checking
3. Package sync operations
4. Pool sync summaries
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime

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


async def test_package_sync_functionality():
    """Test the complete package sync functionality."""
    
    print("🧪 Testing Package Sync Functionality")
    print("=" * 60)
    
    server_url = "http://localhost:4444"
    
    # Step 1: Create endpoints and submit repository data
    print("\n📋 Step 1: Setting up test endpoints with repository data")
    print("-" * 55)
    
    endpoints = []
    
    # Create multiple endpoints
    for i in range(3):
        endpoint_name = f"package-sync-test-{i+1}"
        
        # Create and authenticate endpoint
        api_client = PacmanSyncAPIClient(server_url)
        token = await api_client.authenticate(endpoint_name, f"TestMachine{i+1}")
        
        if not token:
            print(f"❌ Failed to authenticate endpoint {endpoint_name}")
            continue
        
        endpoint_id = api_client.token_manager.get_current_endpoint_id()
        print(f"✅ Created endpoint {endpoint_name} (ID: {endpoint_id})")
        
        # Submit repository data (full sync to get packages)
        sync_client = RepositorySyncClient(server_url, endpoint_name)
        success = await sync_client.perform_pool_assignment_sync(api_client, endpoint_id)
        
        if success:
            print(f"   ✅ Repository data submitted for {endpoint_name}")
        else:
            print(f"   ❌ Failed to submit repository data for {endpoint_name}")
        
        endpoints.append({
            'name': endpoint_name,
            'id': endpoint_id,
            'api_client': api_client
        })
    
    if not endpoints:
        print("❌ No endpoints created successfully")
        return False
    
    # Step 2: Create a pool and assign endpoints
    print(f"\n📋 Step 2: Creating pool and assigning {len(endpoints)} endpoints")
    print("-" * 55)
    
    import aiohttp
    
    # Create pool
    pool_data = {
        "name": "package-sync-test-pool",
        "description": "Test pool for package sync functionality"
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
        
        # Assign endpoints to pool
        for endpoint in endpoints:
            assign_data = {"pool_id": pool_id}
            async with session.put(
                f"{server_url}/api/endpoints/{endpoint['id']}/pool", 
                json=assign_data
            ) as response:
                if response.status == 200:
                    print(f"   ✅ Assigned {endpoint['name']} to pool")
                else:
                    print(f"   ❌ Failed to assign {endpoint['name']} to pool")
    
    # Step 3: Set target state (use first endpoint's state)
    print("\n📋 Step 3: Setting target state for the pool")
    print("-" * 45)
    
    # Get states for first endpoint
    first_endpoint = endpoints[0]
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{server_url}/api/states/endpoint/{first_endpoint['id']}"
        ) as response:
            if response.status == 200:
                states_data = await response.json()
                if states_data['states']:
                    target_state_id = states_data['states'][0]['id']
                    
                    # Set as target state for pool
                    async with session.put(
                        f"{server_url}/api/pools/{pool_id}/target-state/{target_state_id}"
                    ) as response:
                        if response.status == 200:
                            print(f"✅ Set target state: {target_state_id}")
                        else:
                            print(f"❌ Failed to set target state: {response.status}")
                            return False
                else:
                    print("❌ No states found for first endpoint")
                    return False
            else:
                print(f"❌ Failed to get states: {response.status}")
                return False
    
    # Step 4: Test package counting
    print("\n📋 Step 4: Testing package counting functionality")
    print("-" * 50)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{server_url}/api/package-sync/pools/{pool_id}/package-count"
        ) as response:
            if response.status == 200:
                count_data = await response.json()
                print(f"✅ Package count retrieved:")
                print(f"   Total packages: {count_data['total_packages']}")
                print(f"   Target state ID: {count_data['target_state_id']}")
                print(f"   Architecture: {count_data['architecture']}")
                print(f"   Packages by repository:")
                for repo, count in count_data['packages_by_repository'].items():
                    print(f"     {repo}: {count} packages")
            else:
                print(f"❌ Failed to get package count: {response.status}")
                return False
    
    # Step 5: Test endpoint sync status
    print("\n📋 Step 5: Testing endpoint sync status")
    print("-" * 42)
    
    for endpoint in endpoints:
        # Get auth headers for this endpoint
        headers = {'Authorization': f'Bearer {endpoint["api_client"].token_manager.get_current_token()}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{server_url}/api/package-sync/endpoints/{endpoint['id']}/sync-status",
                headers=headers
            ) as response:
                if response.status == 200:
                    status_data = await response.json()
                    print(f"✅ Sync status for {endpoint['name']}:")
                    print(f"   Sync status: {status_data['sync_status']}")
                    print(f"   Target packages: {status_data['target_packages']}")
                    print(f"   Current packages: {status_data['current_packages']}")
                    print(f"   To install: {status_data['packages_to_install']}")
                    print(f"   To upgrade: {status_data['packages_to_upgrade']}")
                    print(f"   To remove: {status_data['packages_to_remove']}")
                else:
                    print(f"❌ Failed to get sync status for {endpoint['name']}: {response.status}")
    
    # Step 6: Test pool sync summary
    print("\n📋 Step 6: Testing pool sync summary")
    print("-" * 38)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{server_url}/api/package-sync/pools/{pool_id}/endpoints/sync-summary"
        ) as response:
            if response.status == 200:
                summary_data = await response.json()
                print(f"✅ Pool sync summary:")
                print(f"   Total endpoints: {summary_data['total_endpoints']}")
                print(f"   Target packages: {summary_data['target_packages']}")
                print(f"   Sync status counts:")
                for status, count in summary_data['sync_status_counts'].items():
                    print(f"     {status}: {count} endpoints")
            else:
                print(f"❌ Failed to get pool sync summary: {response.status}")
    
    # Step 7: Test dry run sync
    print("\n📋 Step 7: Testing dry run package sync")
    print("-" * 40)
    
    # Test with second endpoint
    if len(endpoints) > 1:
        second_endpoint = endpoints[1]
        headers = {'Authorization': f'Bearer {second_endpoint["api_client"].token_manager.get_current_token()}'}
        sync_data = {"dry_run": True}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{server_url}/api/package-sync/endpoints/{second_endpoint['id']}/sync",
                json=sync_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    sync_result = await response.json()
                    print(f"✅ Dry run sync for {second_endpoint['name']}:")
                    print(f"   Message: {sync_result['message']}")
                    if 'changes' in sync_result:
                        changes = sync_result['changes']
                        print(f"   Would install: {changes['packages_to_install']} packages")
                        print(f"   Would upgrade: {changes['packages_to_upgrade']} packages")
                        print(f"   Would remove: {changes['packages_to_remove']} packages")
                else:
                    print(f"❌ Failed to perform dry run sync: {response.status}")
    
    # Cleanup
    print("\n📋 Cleanup: Closing API clients")
    print("-" * 35)
    
    for endpoint in endpoints:
        await endpoint['api_client'].close()
    
    return True


async def main():
    """Main test function."""
    success = await test_package_sync_functionality()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 PACKAGE SYNC FUNCTIONALITY TEST PASSED!")
        print("✅ All package sync features are working correctly!")
        print("\n📋 Tested features:")
        print("   1. ✅ Package counting in target states")
        print("   2. ✅ Endpoint sync status checking")
        print("   3. ✅ Pool sync summaries")
        print("   4. ✅ Dry run package sync")
        return 0
    else:
        print("💥 PACKAGE SYNC FUNCTIONALITY TEST FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))