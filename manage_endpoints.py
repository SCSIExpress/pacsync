#!/usr/bin/env python3
"""
Endpoint management utility for Pacman Sync Utility.
This script helps you list, create, and manage endpoints and pools.
"""

import asyncio
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

SERVER_URL = "http://localhost:4444"

async def list_endpoints():
    """List all endpoints."""
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SERVER_URL}/api/endpoints") as response:
                if response.status == 200:
                    endpoints = await response.json()
                    
                    print("📋 Current Endpoints:")
                    print("=" * 60)
                    
                    if not endpoints:
                        print("   No endpoints found")
                        return []
                    
                    for i, endpoint in enumerate(endpoints, 1):
                        pool_status = f"Pool: {endpoint.get('pool_id', 'Not assigned')}"
                        sync_status = f"Status: {endpoint.get('sync_status', 'unknown')}"
                        last_seen = endpoint.get('last_seen', 'Never')
                        
                        print(f"   {i}. {endpoint.get('name', 'Unknown')}@{endpoint.get('hostname', 'Unknown')}")
                        print(f"      ID: {endpoint.get('id', 'Unknown')}")
                        print(f"      {pool_status}")
                        print(f"      {sync_status}")
                        print(f"      Last seen: {last_seen}")
                        print()
                    
                    return endpoints
                else:
                    print(f"❌ Failed to list endpoints: {response.status}")
                    return []
                    
    except ImportError:
        print("❌ aiohttp not available. Please install: pip install aiohttp")
        return []
    except Exception as e:
        print(f"❌ Error listing endpoints: {e}")
        return []

async def list_pools():
    """List all pools."""
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SERVER_URL}/api/pools") as response:
                if response.status == 200:
                    data = await response.json()
                    pools = data.get('pools', []) if isinstance(data, dict) else data
                    
                    print("🏊 Current Pools:")
                    print("=" * 40)
                    
                    if not pools:
                        print("   No pools found")
                        return []
                    
                    for i, pool in enumerate(pools, 1):
                        endpoint_count = len(pool.get('endpoints', []))
                        
                        print(f"   {i}. {pool.get('name', 'Unknown')}")
                        print(f"      ID: {pool.get('id', 'Unknown')}")
                        print(f"      Description: {pool.get('description', 'No description')}")
                        print(f"      Endpoints: {endpoint_count}")
                        print()
                    
                    return pools
                else:
                    print(f"❌ Failed to list pools: {response.status}")
                    return []
                    
    except Exception as e:
        print(f"❌ Error listing pools: {e}")
        return []

async def create_pool(name, description=""):
    """Create a new pool."""
    try:
        import aiohttp
        
        pool_data = {
            "name": name,
            "description": description or f"Pool created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{SERVER_URL}/api/pools", json=pool_data) as response:
                if response.status == 200:
                    data = await response.json()
                    pool_id = data.get('id') or data.get('pool_id')
                    print(f"✅ Pool created successfully!")
                    print(f"   Name: {name}")
                    print(f"   ID: {pool_id}")
                    return pool_id
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to create pool: {response.status} - {error_text}")
                    return None
                    
    except Exception as e:
        print(f"❌ Error creating pool: {e}")
        return None

async def assign_endpoint_to_pool(endpoint_id, pool_id):
    """Assign an endpoint to a pool."""
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{SERVER_URL}/api/endpoints/{endpoint_id}/pool",
                params={"pool_id": pool_id}
            ) as response:
                if response.status == 200:
                    print(f"✅ Endpoint {endpoint_id} assigned to pool {pool_id}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to assign endpoint: {response.status} - {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error assigning endpoint: {e}")
        return False

async def delete_endpoint(endpoint_id, auth_token):
    """Delete an endpoint (requires auth token)."""
    try:
        import aiohttp
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{SERVER_URL}/api/endpoints/{endpoint_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    print(f"✅ Endpoint {endpoint_id} deleted successfully")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to delete endpoint: {response.status} - {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error deleting endpoint: {e}")
        return False

def print_menu():
    """Print the main menu."""
    print("\n🛠️  Pacman Sync Utility - Endpoint Manager")
    print("=" * 50)
    print("1. List all endpoints")
    print("2. List all pools")
    print("3. Create a new pool")
    print("4. Assign endpoint to pool")
    print("5. Create test endpoint and pool setup (RECOMMENDED)")
    print("6. Set target state for pool (requires auth token)")
    print("7. Clean up test endpoints (requires manual token input)")
    print("0. Exit")
    print()

async def setup_test_environment():
    """Set up a complete test environment."""
    print("🚀 Setting up test environment...")
    
    # Create test pool
    pool_id = await create_pool("test-pool", "Test pool for sync operations")
    if not pool_id:
        print("❌ Failed to create test pool")
        return False
    
    # Create test endpoint
    try:
        import aiohttp
        
        endpoint_data = {
            "name": "test-client",
            "hostname": "test-machine"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{SERVER_URL}/api/endpoints/register",
                json=endpoint_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    endpoint_id = data['endpoint']['id']
                    auth_token = data['auth_token']
                    
                    print(f"✅ Test endpoint created!")
                    print(f"   Endpoint ID: {endpoint_id}")
                    print(f"   Auth Token: {auth_token[:20]}...")
                    
                    # Assign to pool
                    success = await assign_endpoint_to_pool(endpoint_id, pool_id)
                    if success:
                        print("✅ Endpoint assigned to pool")
                        
                        # Set up initial target state
                        print("🎯 Setting up initial target state...")
                        headers = {"Authorization": f"Bearer {auth_token}"}
                        
                        # Submit a mock state
                        state_data = {
                            "endpoint_id": endpoint_id,
                            "timestamp": datetime.now().isoformat(),
                            "packages": [
                                {
                                    "package_name": "base",
                                    "version": "3-1",
                                    "repository": "core",
                                    "installed_size": 1024,
                                    "dependencies": []
                                },
                                {
                                    "package_name": "linux",
                                    "version": "6.6.8-1",
                                    "repository": "core",
                                    "installed_size": 134217728,
                                    "dependencies": ["base"]
                                }
                            ],
                            "pacman_version": "6.0.2",
                            "architecture": "x86_64"
                        }
                        
                        # Submit state
                        async with session.post(
                            f"{SERVER_URL}/api/states/{endpoint_id}",
                            json=state_data,
                            headers=headers
                        ) as state_response:
                            if state_response.status == 200:
                                print("✅ Initial state submitted")
                            else:
                                print(f"⚠️  State submission failed: {state_response.status}")
                        
                        # Set as target
                        async with session.post(
                            f"{SERVER_URL}/api/sync/{endpoint_id}/set-as-latest",
                            json={},
                            headers=headers
                        ) as target_response:
                            if target_response.status == 200:
                                print("✅ Target state set for pool")
                            else:
                                print(f"⚠️  Set-as-latest failed: {target_response.status}")
                        
                        print("🎉 Complete test environment setup finished!")
                        print(f"📋 Summary:")
                        print(f"   Pool ID: {pool_id}")
                        print(f"   Endpoint ID: {endpoint_id}")
                        print(f"   Target state: Set")
                        print(f"   Ready for sync tests: ✅")
                        return True
                    else:
                        print("⚠️  Endpoint created but pool assignment failed")
                        return False
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to create endpoint: {response.status} - {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error setting up test environment: {e}")
        return False

async def main():
    """Main interactive menu."""
    
    while True:
        print_menu()
        
        try:
            choice = input("Enter your choice (0-6): ").strip()
            
            if choice == "0":
                print("👋 Goodbye!")
                break
            elif choice == "1":
                await list_endpoints()
            elif choice == "2":
                await list_pools()
            elif choice == "3":
                name = input("Enter pool name: ").strip()
                if name:
                    description = input("Enter description (optional): ").strip()
                    await create_pool(name, description)
                else:
                    print("❌ Pool name is required")
            elif choice == "4":
                endpoints = await list_endpoints()
                pools = await list_pools()
                
                if not endpoints:
                    print("❌ No endpoints available")
                    continue
                if not pools:
                    print("❌ No pools available")
                    continue
                
                try:
                    endpoint_idx = int(input(f"Select endpoint (1-{len(endpoints)}): ")) - 1
                    pool_idx = int(input(f"Select pool (1-{len(pools)}): ")) - 1
                    
                    if 0 <= endpoint_idx < len(endpoints) and 0 <= pool_idx < len(pools):
                        endpoint_id = endpoints[endpoint_idx]['id']
                        pool_id = pools[pool_idx]['id']
                        await assign_endpoint_to_pool(endpoint_id, pool_id)
                    else:
                        print("❌ Invalid selection")
                except ValueError:
                    print("❌ Please enter valid numbers")
            elif choice == "5":
                await setup_test_environment()
            elif choice == "6":
                print("🎯 Set Target State for Pool")
                print("This requires an auth token from endpoint registration")
                
                endpoints = await list_endpoints()
                if not endpoints:
                    print("❌ No endpoints available")
                    continue
                
                try:
                    endpoint_idx = int(input(f"Select endpoint (1-{len(endpoints)}): ")) - 1
                    if 0 <= endpoint_idx < len(endpoints):
                        endpoint_id = endpoints[endpoint_idx]['id']
                        auth_token = input("Enter auth token for this endpoint: ").strip()
                        
                        if auth_token:
                            # This would set the endpoint's current state as target
                            print("⚠️  This feature needs to be implemented")
                            print("   Use option 5 to create a complete test setup instead")
                        else:
                            print("❌ Auth token is required")
                    else:
                        print("❌ Invalid selection")
                except ValueError:
                    print("❌ Please enter valid numbers")
            elif choice == "7":
                print("⚠️  This feature requires manual implementation")
                print("   You need auth tokens to delete endpoints")
            else:
                print("❌ Invalid choice")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")