#!/usr/bin/env python3
"""
Test script for client automatic pool assignment.

This script tests that the client automatically assigns itself to a pool
when pool_id is configured, which should fix the "failed to submit state to server" error.
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
    """Create a test pool for assignment."""
    print("\n🏊 Creating test pool...")
    
    async with aiohttp.ClientSession() as session:
        import time
        pool_data = {
            "name": f"auto-assign-test-pool-{int(time.time())}",
            "description": "Test pool for automatic assignment"
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


async def test_client_with_pool_config(pool_id: str):
    """Test client startup with pool configuration."""
    print(f"\n🔧 Testing client with pool_id: {pool_id}")
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
        config_content = f"""
[server]
url = {SERVER_URL}
timeout = 30

[client]
endpoint_name = auto-assign-test-endpoint
pool_id = {pool_id}
auto_sync = false

[ui]
show_notifications = false
minimize_to_tray = false
"""
        f.write(config_content)
        config_path = f.name
    
    try:
        # Import client components
        from client.config import ClientConfiguration
        from client.auth.token_manager import TokenManager
        from client.api_client import PacmanSyncAPIClient
        
        # Create configuration
        config = ClientConfiguration(config_path)
        
        # Verify pool_id is loaded
        loaded_pool_id = config.get_pool_id()
        print(f"📋 Loaded pool_id from config: {loaded_pool_id}")
        
        if loaded_pool_id != pool_id:
            print(f"❌ Config pool_id mismatch: expected {pool_id}, got {loaded_pool_id}")
            return False
        
        # Create API client
        server_url = config.get_server_url()
        api_client = PacmanSyncAPIClient(server_url)
        
        # Update the API client's token manager with config
        api_client.token_manager.config = config
        
        # Test authentication (which should trigger pool assignment)
        print("🔐 Testing authentication with automatic pool assignment...")
        
        endpoint_name = config.get_endpoint_name()
        hostname = "test-host"
        
        success = await api_client.token_manager.authenticate(endpoint_name, hostname, SERVER_URL)
        
        if success:
            endpoint_id = api_client.token_manager.get_current_endpoint_id()
            print(f"✅ Authentication successful, endpoint_id: {endpoint_id}")
            
            # Verify endpoint is assigned to pool
            await asyncio.sleep(1)  # Give pool assignment time to complete
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{SERVER_URL}/api/endpoints/{endpoint_id}") as response:
                    if response.status == 200:
                        endpoint_data = await response.json()
                        assigned_pool_id = endpoint_data.get('pool_id')
                        
                        if assigned_pool_id == pool_id:
                            print(f"✅ Endpoint automatically assigned to pool: {assigned_pool_id}")
                            
                            # Test state submission (this should now work)
                            print("📤 Testing state submission...")
                            return await test_state_submission_with_client(api_client, endpoint_id)
                        else:
                            print(f"❌ Endpoint not assigned to correct pool: expected {pool_id}, got {assigned_pool_id}")
                            return False
                    else:
                        print(f"❌ Failed to get endpoint info: {response.status}")
                        return False
        else:
            print("❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing client: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up config file
        try:
            os.unlink(config_path)
        except:
            pass


async def test_state_submission_with_client(api_client, endpoint_id: str):
    """Test state submission using the client API."""
    print("📤 Testing state submission with client API...")
    
    try:
        # Create a mock system state
        from shared.models import SystemState, PackageState
        from datetime import datetime
        
        packages = [
            PackageState(
                package_name="test-package-1",
                version="1.0.0",
                repository="core",
                installed_size=1024000,
                dependencies=["glibc"]
            ),
            PackageState(
                package_name="test-package-2",
                version="2.0.0",
                repository="extra",
                installed_size=2048000,
                dependencies=["test-package-1"]
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
            print("❌ State submission returned empty state_id")
            return False
            
    except Exception as e:
        print(f"❌ State submission failed: {e}")
        return False


async def main():
    """Run the test."""
    print("🧪 Client Automatic Pool Assignment Test")
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
    
    # Test client with pool configuration
    if await test_client_with_pool_config(pool_id):
        print("\n🎉 Client automatic pool assignment test passed!")
        print("   The 'failed to submit state to server' error should now be fixed.")
        return 0
    else:
        print("\n❌ Client automatic pool assignment test failed!")
        print("   Check the error messages above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))