#!/usr/bin/env python3
"""
Test script for server-side pool assignment.

This script tests that clients can query their pool assignment from the server
and sync pool changes automatically.
"""

import asyncio
import aiohttp
import json
import sys
import tempfile
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

SERVER_URL = "http://localhost:4444"


async def test_server_health():
    """Test if server is running."""
    print("🏥 Testing server health...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SERVER_URL}/health/live") as response:
                if response.status == 200:
                    print("✅ Server is healthy")
                    return True
                else:
                    print(f"❌ Server health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False


async def create_test_pool():
    """Create a test pool."""
    print("\n🏊 Creating test pool...")
    
    async with aiohttp.ClientSession() as session:
        import time
        pool_data = {
            "name": f"server-assign-test-pool-{int(time.time())}",
            "description": "Test pool for server-side assignment"
        }
        
        try:
            async with session.post(f"{SERVER_URL}/api/pools", json=pool_data) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    pool_id = result["id"]
                    print(f"✅ Created test pool: {pool_id}")
                    return pool_id
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to create pool: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Error creating pool: {e}")
            return None


async def create_test_endpoint():
    """Create a test endpoint."""
    print("\n🔧 Creating test endpoint...")
    
    async with aiohttp.ClientSession() as session:
        endpoint_data = {
            "name": "server-assign-test-endpoint",
            "hostname": "test-host"
        }
        
        try:
            async with session.post(f"{SERVER_URL}/api/endpoints/register", json=endpoint_data) as response:
                if response.status == 200:
                    result = await response.json()
                    endpoint_id = result["endpoint"]["id"]
                    auth_token = result["auth_token"]
                    print(f"✅ Created endpoint: {endpoint_id}")
                    return endpoint_id, auth_token
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to create endpoint: {response.status} - {error_text}")
                    return None, None
        except Exception as e:
            print(f"❌ Error creating endpoint: {e}")
            return None, None


async def test_pool_assignment_query(endpoint_id: str, auth_token: str):
    """Test querying pool assignment before assignment."""
    print(f"\n🔍 Testing pool assignment query (before assignment)...")
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        try:
            # First test if the endpoint exists at all
            print(f"   Testing route: /api/endpoints/{endpoint_id}/pool")
            
            async with session.get(
                f"{SERVER_URL}/api/endpoints/{endpoint_id}/pool",
                headers=headers
            ) as response:
                print(f"   Response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Pool assignment query successful:")
                    print(f"   Endpoint ID: {result.get('endpoint_id')}")
                    print(f"   Pool ID: {result.get('pool_id')}")
                    print(f"   Pool Assigned: {result.get('pool_assigned')}")
                    print(f"   Sync Status: {result.get('sync_status')}")
                    return result
                elif response.status == 401:
                    print(f"⚠️  Authentication error - checking if route exists...")
                    # Try without auth to see if route exists
                    async with session.get(f"{SERVER_URL}/api/endpoints/{endpoint_id}/pool") as no_auth_response:
                        if no_auth_response.status == 401:
                            print(f"✅ Route exists but requires authentication (expected)")
                            print(f"❌ Auth token might be invalid or expired")
                        else:
                            print(f"❌ Route issue: {no_auth_response.status}")
                    return None
                elif response.status == 404:
                    print(f"❌ Route not found - server might need restart to pick up new routes")
                    return None
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to query pool assignment: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Error querying pool assignment: {e}")
            return None


async def assign_endpoint_to_pool_server_side(endpoint_id: str, pool_id: str):
    """Assign endpoint to pool via server API (simulating web UI action)."""
    print(f"\n🔗 Assigning endpoint to pool (server-side)...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.put(
                f"{SERVER_URL}/api/endpoints/{endpoint_id}/pool",
                params={"pool_id": pool_id}
            ) as response:
                if response.status == 200:
                    print(f"✅ Server-side assignment successful")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to assign endpoint: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Error assigning endpoint: {e}")
            return False


async def test_client_pool_sync(endpoint_id: str, auth_token: str, expected_pool_id: str):
    """Test client pool sync functionality."""
    print(f"\n🔄 Testing client pool sync...")
    
    # Create temporary config file (without pool_id)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        config_content = f"""
[server]
url = {SERVER_URL}
timeout = 30

[client]
endpoint_name = server-assign-test-endpoint
# No pool_id configured - should be synced from server

[ui]
show_notifications = false
minimize_to_tray = false
"""
        f.write(config_content)
        config_path = f.name
    
    try:
        # Import client components
        from client.config import ClientConfiguration
        from client.api_client import PacmanSyncAPIClient
        
        # Create configuration
        config = ClientConfiguration(config_path)
        
        # Verify no pool_id is configured initially
        initial_pool_id = config.get_pool_id()
        print(f"📋 Initial pool_id from config: {initial_pool_id}")
        
        # Create API client
        server_url = config.get_server_url()
        api_client = PacmanSyncAPIClient(server_url)
        
        # Manually set the auth token (simulating authenticated client)
        api_client.token_manager._current_endpoint_id = endpoint_id
        api_client.token_manager._current_token = auth_token
        api_client.token_manager.config = config
        
        # Test pool assignment query
        print("🔍 Querying pool assignment from client...")
        pool_info = await api_client.get_pool_assignment(endpoint_id)
        
        if pool_info:
            print(f"✅ Client retrieved pool assignment:")
            print(f"   Pool ID: {pool_info.get('pool_id')}")
            print(f"   Pool Assigned: {pool_info.get('pool_assigned')}")
            print(f"   Sync Status: {pool_info.get('sync_status')}")
            
            # Verify the pool_id matches what we assigned
            if pool_info.get('pool_id') == expected_pool_id:
                print(f"✅ Pool assignment matches expected: {expected_pool_id}")
                
                # Test sync pool status
                print("🔄 Testing sync pool status...")
                synced_info = await api_client.token_manager.sync_pool_status()
                
                if synced_info:
                    print(f"✅ Pool status synced successfully")
                    
                    # Check if config was updated
                    updated_pool_id = config.get_pool_id()
                    print(f"📋 Updated pool_id in config: {updated_pool_id}")
                    
                    if updated_pool_id == expected_pool_id:
                        print(f"✅ Config updated with server-assigned pool_id")
                        return True
                    else:
                        print(f"❌ Config not updated correctly: expected {expected_pool_id}, got {updated_pool_id}")
                        return False
                else:
                    print(f"❌ Failed to sync pool status")
                    return False
            else:
                print(f"❌ Pool assignment mismatch: expected {expected_pool_id}, got {pool_info.get('pool_id')}")
                return False
        else:
            print(f"❌ Failed to retrieve pool assignment")
            return False
            
    except Exception as e:
        print(f"❌ Error testing client pool sync: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up config file
        try:
            os.unlink(config_path)
        except:
            pass


async def test_state_submission_after_sync(endpoint_id: str, auth_token: str):
    """Test that state submission works after pool sync."""
    print(f"\n📤 Testing state submission after pool sync...")
    
    try:
        # Create API client
        from client.api_client import PacmanSyncAPIClient
        from shared.models import SystemState, PackageState
        
        api_client = PacmanSyncAPIClient(SERVER_URL)
        
        # Set auth token
        api_client.token_manager._current_endpoint_id = endpoint_id
        api_client.token_manager._current_token = auth_token
        
        # Create mock system state
        packages = [
            PackageState(
                package_name="test-package",
                version="1.0.0",
                repository="core",
                installed_size=1024000,
                dependencies=["glibc"]
            )
        ]
        
        system_state = SystemState(
            endpoint_id=endpoint_id,
            timestamp=datetime.now(),
            packages=packages,
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        # Submit state
        state_id = await api_client.submit_state(endpoint_id, system_state)
        
        if state_id:
            print(f"✅ State submitted successfully: {state_id}")
            return True
        else:
            print("❌ State submission failed")
            return False
            
    except Exception as e:
        print(f"❌ State submission error: {e}")
        return False


async def main():
    """Run the test."""
    print("🧪 Server-Side Pool Assignment Test")
    print("=" * 50)
    
    # Test server health
    if not await test_server_health():
        print("\n❌ Server is not available. Please start the server first.")
        return 1
    
    # Create test pool
    pool_id = await create_test_pool()
    if not pool_id:
        print("\n❌ Failed to create test pool. Cannot continue.")
        return 1
    
    # Create test endpoint
    endpoint_id, auth_token = await create_test_endpoint()
    if not endpoint_id or not auth_token:
        print("\n❌ Failed to create test endpoint. Cannot continue.")
        return 1
    
    # Test pool assignment query (before assignment)
    initial_assignment = await test_pool_assignment_query(endpoint_id, auth_token)
    if not initial_assignment:
        print("\n❌ Failed to query initial pool assignment. Cannot continue.")
        return 1
    
    if initial_assignment.get('pool_assigned'):
        print("\n⚠️  Endpoint is already assigned to a pool. This is unexpected.")
    
    # Assign endpoint to pool (server-side)
    if not await assign_endpoint_to_pool_server_side(endpoint_id, pool_id):
        print("\n❌ Failed to assign endpoint to pool. Cannot continue.")
        return 1
    
    # Test pool assignment query (after assignment)
    final_assignment = await test_pool_assignment_query(endpoint_id, auth_token)
    if not final_assignment:
        print("\n❌ Failed to query final pool assignment. Cannot continue.")
        return 1
    
    # Test client pool sync
    if not await test_client_pool_sync(endpoint_id, auth_token, pool_id):
        print("\n❌ Client pool sync test failed.")
        return 1
    
    # Test state submission
    if not await test_state_submission_after_sync(endpoint_id, auth_token):
        print("\n❌ State submission test failed.")
        return 1
    
    print("\n🎉 Server-side pool assignment test passed!")
    print("   ✅ Endpoints can query their pool assignment from server")
    print("   ✅ Clients can sync pool assignment changes")
    print("   ✅ Config is updated with server-assigned pool_id")
    print("   ✅ State submission works after pool sync")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))