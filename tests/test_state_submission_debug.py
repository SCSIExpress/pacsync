#!/usr/bin/env python3
"""
Debug script for state submission issues.

This script tests the state submission endpoint to identify
why the client is getting "failed to submit state to server" errors.
"""

import asyncio
import aiohttp
import json
import sys
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


async def test_endpoint_creation():
    """Test creating an endpoint and getting auth token."""
    print("\n🔧 Testing endpoint creation...")
    
    async with aiohttp.ClientSession() as session:
        endpoint_data = {
            "name": "debug-test-endpoint",
            "hostname": "debug-host"
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


async def test_pool_creation_and_assignment(endpoint_id: str, auth_token: str):
    """Create a pool and assign the endpoint to it."""
    print(f"\n🏊 Creating pool and assigning endpoint...")
    
    async with aiohttp.ClientSession() as session:
        # Create a pool with unique name
        import time
        pool_data = {
            "name": f"debug-test-pool-{int(time.time())}",
            "description": "Test pool for debugging state submission"
        }
        
        try:
            async with session.post(f"{SERVER_URL}/api/pools", json=pool_data) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    pool_id = result["id"]
                    print(f"✅ Created pool: {pool_id}")
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to create pool: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Error creating pool: {e}")
            return False
        
        # Assign endpoint to pool
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        try:
            async with session.put(
                f"{SERVER_URL}/api/endpoints/{endpoint_id}/pool",
                params={"pool_id": pool_id},
                headers=headers
            ) as response:
                if response.status == 200:
                    print(f"✅ Assigned endpoint to pool")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to assign endpoint to pool: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Error assigning endpoint to pool: {e}")
            return False


async def test_state_submission(endpoint_id: str, auth_token: str):
    """Test submitting state data."""
    print(f"\n📤 Testing state submission for endpoint: {endpoint_id}")
    
    # Create test state data
    state_data = {
        "endpoint_id": endpoint_id,
        "timestamp": datetime.now().isoformat(),
        "packages": [
            {
                "package_name": "test-package",
                "version": "1.0.0",
                "repository": "core",
                "installed_size": 1024000,
                "dependencies": ["glibc", "gcc-libs"]
            },
            {
                "package_name": "another-package",
                "version": "2.1.0",
                "repository": "extra",
                "installed_size": 2048000,
                "dependencies": ["test-package"]
            }
        ],
        "pacman_version": "6.0.1",
        "architecture": "x86_64"
    }
    
    print(f"📋 State data preview:")
    print(f"   Endpoint ID: {state_data['endpoint_id']}")
    print(f"   Timestamp: {state_data['timestamp']}")
    print(f"   Packages: {len(state_data['packages'])}")
    print(f"   Pacman version: {state_data['pacman_version']}")
    print(f"   Architecture: {state_data['architecture']}")
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        try:
            async with session.post(
                f"{SERVER_URL}/api/states/{endpoint_id}",
                json=state_data,
                headers=headers
            ) as response:
                print(f"\n📡 Response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ State submitted successfully!")
                    print(f"   State ID: {result.get('state_id', 'N/A')}")
                    print(f"   Message: {result.get('message', 'N/A')}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ State submission failed: {response.status}")
                    print(f"   Error: {error_text}")
                    
                    # Try to parse error as JSON for better formatting
                    try:
                        error_json = json.loads(error_text)
                        print(f"   Detail: {error_json.get('detail', 'N/A')}")
                    except:
                        pass
                    
                    return False
                    
        except Exception as e:
            print(f"❌ Error during state submission: {e}")
            return False


async def test_states_endpoint_availability():
    """Test if the states endpoint is available."""
    print("\n🔍 Testing states endpoint availability...")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test with invalid endpoint ID to see if endpoint exists
            async with session.post(f"{SERVER_URL}/api/states/invalid-id", json={}) as response:
                print(f"📡 Response status: {response.status}")
                
                if response.status == 401:
                    print("✅ States endpoint exists (got auth error as expected)")
                    return True
                elif response.status == 404:
                    print("❌ States endpoint not found")
                    return False
                else:
                    print(f"✅ States endpoint exists (got status {response.status})")
                    return True
                    
        except Exception as e:
            print(f"❌ Error testing states endpoint: {e}")
            return False


async def test_auth_token_validity(endpoint_id: str, auth_token: str):
    """Test if the auth token is valid."""
    print(f"\n🔐 Testing auth token validity...")
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        try:
            # Try to get endpoint info to test auth
            async with session.get(
                f"{SERVER_URL}/api/endpoints/{endpoint_id}",
                headers=headers
            ) as response:
                print(f"📡 Auth test response status: {response.status}")
                
                if response.status == 200:
                    print("✅ Auth token is valid")
                    return True
                elif response.status == 401:
                    print("❌ Auth token is invalid or expired")
                    return False
                else:
                    print(f"⚠️  Unexpected auth response: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error testing auth token: {e}")
            return False


async def main():
    """Run all debug tests."""
    print("🐛 State Submission Debug Test")
    print("=" * 50)
    
    # Test server health
    if not await test_server_health():
        print("\n❌ Server is not available. Please start the server first.")
        return 1
    
    # Test states endpoint availability
    if not await test_states_endpoint_availability():
        print("\n❌ States endpoint is not available. Check server configuration.")
        return 1
    
    # Create endpoint
    endpoint_id, auth_token = await test_endpoint_creation()
    if not endpoint_id or not auth_token:
        print("\n❌ Failed to create endpoint. Cannot continue.")
        return 1
    
    # Test auth token
    if not await test_auth_token_validity(endpoint_id, auth_token):
        print("\n❌ Auth token is invalid. Cannot continue.")
        return 1
    
    # Create pool and assign endpoint
    if not await test_pool_creation_and_assignment(endpoint_id, auth_token):
        print("\n❌ Failed to create pool or assign endpoint. Cannot continue.")
        return 1
    
    # Test state submission
    if await test_state_submission(endpoint_id, auth_token):
        print("\n🎉 State submission test passed!")
        print("   The server-side state submission is working correctly.")
        print("   The issue might be in the client-side code or configuration.")
        return 0
    else:
        print("\n❌ State submission test failed!")
        print("   Check the error messages above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))