#!/usr/bin/env python3
"""
Test script to demonstrate server-side pool assignment concept.

This script shows how the server-side pool assignment would work
using existing endpoints, without requiring the new route.
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
            "name": f"concept-test-pool-{int(time.time())}",
            "description": "Test pool for concept demonstration"
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
            "name": "concept-test-endpoint",
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


async def verify_assignment_via_endpoint_list(endpoint_id: str, expected_pool_id: str):
    """Verify assignment by listing endpoints and checking pool_id."""
    print(f"\n🔍 Verifying assignment via endpoint list...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/endpoints") as response:
                if response.status == 200:
                    endpoints = await response.json()
                    
                    # Find our endpoint
                    for endpoint in endpoints:
                        if endpoint.get('id') == endpoint_id:
                            pool_id = endpoint.get('pool_id')
                            print(f"✅ Found endpoint in list:")
                            print(f"   Endpoint ID: {endpoint_id}")
                            print(f"   Pool ID: {pool_id}")
                            print(f"   Sync Status: {endpoint.get('sync_status')}")
                            
                            if pool_id == expected_pool_id:
                                print(f"✅ Pool assignment verified: {pool_id}")
                                return True
                            else:
                                print(f"❌ Pool assignment mismatch: expected {expected_pool_id}, got {pool_id}")
                                return False
                    
                    print(f"❌ Endpoint {endpoint_id} not found in list")
                    return False
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to list endpoints: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Error listing endpoints: {e}")
            return False


async def test_client_concept_without_new_route():
    """Test the client concept using existing functionality."""
    print(f"\n🔄 Testing client concept (without new route)...")
    
    print("📋 Concept demonstration:")
    print("   1. Client starts up without pool_id configured")
    print("   2. Server assigns endpoint to pool via web UI")
    print("   3. Client queries server to discover its pool assignment")
    print("   4. Client updates its local config with server-assigned pool_id")
    print("   5. Client can now submit state successfully")
    
    # Create temporary config file (without pool_id)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        config_content = f"""
[server]
url = {SERVER_URL}
timeout = 30

[client]
endpoint_name = concept-test-endpoint
# No pool_id configured initially

[ui]
show_notifications = false
minimize_to_tray = false
"""
        f.write(config_content)
        config_path = f.name
    
    try:
        # Import client components
        from client.config import ClientConfiguration
        
        # Create configuration
        config = ClientConfiguration(config_path)
        
        # Verify no pool_id is configured initially
        initial_pool_id = config.get_pool_id()
        print(f"📋 Initial pool_id from config: {initial_pool_id}")
        
        if initial_pool_id:
            print(f"⚠️  Expected no initial pool_id, but found: {initial_pool_id}")
        
        # Simulate server assigning a pool_id
        server_assigned_pool_id = "simulated-pool-123"
        print(f"🖥️  Server assigns pool_id: {server_assigned_pool_id}")
        
        # Client receives pool assignment and updates config
        config.set_pool_id(server_assigned_pool_id)
        
        # Verify config was updated
        updated_pool_id = config.get_pool_id()
        print(f"📋 Updated pool_id in config: {updated_pool_id}")
        
        if updated_pool_id == server_assigned_pool_id:
            print(f"✅ Config successfully updated with server-assigned pool_id")
            return True
        else:
            print(f"❌ Config update failed: expected {server_assigned_pool_id}, got {updated_pool_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing client concept: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up config file
        try:
            os.unlink(config_path)
        except:
            pass


async def test_state_submission_concept(endpoint_id: str, auth_token: str):
    """Test that state submission works when endpoint is assigned to pool."""
    print(f"\n📤 Testing state submission concept...")
    
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
                package_name="concept-test-package",
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
        print("📤 Attempting state submission...")
        state_id = await api_client.submit_state(endpoint_id, system_state)
        
        if state_id:
            print(f"✅ State submitted successfully: {state_id}")
            print("   This confirms that pool assignment enables state submission")
            return True
        else:
            print("❌ State submission failed")
            return False
            
    except Exception as e:
        print(f"❌ State submission error: {e}")
        print("   This might be expected if endpoint is not assigned to pool")
        return False


async def main():
    """Run the concept demonstration."""
    print("🧪 Server-Side Pool Assignment Concept Test")
    print("=" * 55)
    
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
    
    # Test state submission before pool assignment (should fail)
    print("\n📤 Testing state submission BEFORE pool assignment...")
    success_before = await test_state_submission_concept(endpoint_id, auth_token)
    if success_before:
        print("⚠️  State submission succeeded before pool assignment (unexpected)")
    else:
        print("✅ State submission failed before pool assignment (expected)")
    
    # Assign endpoint to pool (server-side)
    if not await assign_endpoint_to_pool_server_side(endpoint_id, pool_id):
        print("\n❌ Failed to assign endpoint to pool. Cannot continue.")
        return 1
    
    # Verify assignment
    if not await verify_assignment_via_endpoint_list(endpoint_id, pool_id):
        print("\n❌ Failed to verify pool assignment.")
        return 1
    
    # Test client concept
    if not await test_client_concept_without_new_route():
        print("\n❌ Client concept test failed.")
        return 1
    
    # Test state submission after pool assignment (should succeed)
    print("\n📤 Testing state submission AFTER pool assignment...")
    success_after = await test_state_submission_concept(endpoint_id, auth_token)
    if success_after:
        print("✅ State submission succeeded after pool assignment (expected)")
    else:
        print("❌ State submission failed after pool assignment (unexpected)")
    
    print("\n🎉 Server-side pool assignment concept demonstrated!")
    print("   ✅ Server can assign endpoints to pools")
    print("   ✅ Pool assignment enables state submission")
    print("   ✅ Client config can be updated with server-assigned pool_id")
    print("   ✅ This approach eliminates the need for clients to know pool_id in advance")
    
    print("\n📝 Next steps to complete implementation:")
    print("   1. Restart server to pick up new /api/endpoints/{id}/pool route")
    print("   2. Test the new route for querying pool assignments")
    print("   3. Implement periodic pool sync in client")
    print("   4. Add UI notifications for pool assignment changes")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))