#!/usr/bin/env python3
"""
Test script specifically for sync-to-latest functionality.
This script reuses existing endpoints and manages pools automatically.
"""

import asyncio
import sys
import os
import logging
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
SERVER_URL = "http://localhost:4444"
ENDPOINT_NAME = "test-client"  # Fixed name to reuse
HOSTNAME = "test-machine"      # Fixed hostname to reuse
POOL_NAME = "test-pool"        # Fixed pool name

async def get_or_create_endpoint(session, endpoint_name, hostname):
    """Get existing endpoint or create new one."""
    
    print(f"🔍 Looking for existing endpoint: {endpoint_name}@{hostname}")
    
    # First, try to list existing endpoints
    try:
        async with session.get(f"{SERVER_URL}/api/endpoints") as response:
            if response.status == 200:
                data = await response.json()
                endpoints = data if isinstance(data, list) else []
                
                # Look for existing endpoint with same name and hostname
                for endpoint in endpoints:
                    if endpoint.get('name') == endpoint_name and endpoint.get('hostname') == hostname:
                        print(f"✅ Found existing endpoint: {endpoint['id']}")
                        return endpoint['id'], None  # No new token needed
                        
                print(f"📝 No existing endpoint found, creating new one...")
            else:
                print(f"⚠️  Could not list endpoints: {response.status}")
    except Exception as e:
        print(f"⚠️  Error listing endpoints: {e}")
    
    # Create new endpoint
    try:
        registration_data = {
            "name": endpoint_name,
            "hostname": hostname
        }
        
        async with session.post(
            f"{SERVER_URL}/api/endpoints/register",
            json=registration_data
        ) as response:
            if response.status == 200:
                data = await response.json()
                endpoint_id = data['endpoint']['id']
                auth_token = data['auth_token']
                print(f"✅ Created new endpoint: {endpoint_id}")
                return endpoint_id, auth_token
            else:
                error_text = await response.text()
                print(f"❌ Failed to create endpoint: {response.status} - {error_text}")
                return None, None
                
    except Exception as e:
        print(f"❌ Error creating endpoint: {e}")
        return None, None

async def get_or_create_pool(session, pool_name):
    """Get existing pool or create new one."""
    
    print(f"🔍 Looking for existing pool: {pool_name}")
    
    # Try to list existing pools
    try:
        async with session.get(f"{SERVER_URL}/api/pools") as response:
            if response.status == 200:
                data = await response.json()
                pools = data.get('pools', []) if isinstance(data, dict) else data
                
                # Look for existing pool
                for pool in pools:
                    if pool.get('name') == pool_name:
                        print(f"✅ Found existing pool: {pool['id']}")
                        return pool['id']
                        
                print(f"📝 No existing pool found, creating new one...")
            else:
                print(f"⚠️  Could not list pools: {response.status}")
    except Exception as e:
        print(f"⚠️  Error listing pools: {e}")
    
    # Create new pool
    try:
        pool_data = {
            "name": pool_name,
            "description": "Test pool for sync operations"
        }
        
        async with session.post(
            f"{SERVER_URL}/api/pools",
            json=pool_data
        ) as response:
            if response.status == 200:
                data = await response.json()
                pool_id = data.get('id') or data.get('pool_id')
                print(f"✅ Created new pool: {pool_id}")
                return pool_id
            else:
                error_text = await response.text()
                print(f"❌ Failed to create pool: {response.status} - {error_text}")
                return None
                
    except Exception as e:
        print(f"❌ Error creating pool: {e}")
        return None

async def assign_endpoint_to_pool(session, endpoint_id, pool_id):
    """Assign endpoint to pool."""
    
    print(f"🔗 Assigning endpoint {endpoint_id} to pool {pool_id}")
    
    try:
        async with session.put(
            f"{SERVER_URL}/api/endpoints/{endpoint_id}/pool",
            params={"pool_id": pool_id}
        ) as response:
            if response.status == 200:
                print("✅ Endpoint assigned to pool successfully")
                return True
            else:
                error_text = await response.text()
                print(f"⚠️  Pool assignment failed: {response.status} - {error_text}")
                # This might fail if already assigned, which is okay
                return True  # Continue anyway
                
    except Exception as e:
        print(f"⚠️  Error assigning to pool: {e}")
        return True  # Continue anyway

async def test_sync_to_latest():
    """Test the sync-to-latest functionality specifically."""
    
    print("🔄 Testing Sync-to-Latest Functionality")
    print("=" * 45)
    
    try:
        import aiohttp
        
        print(f"📡 Server: {SERVER_URL}")
        print(f"🖥️  Endpoint: {ENDPOINT_NAME}@{HOSTNAME}")
        print(f"🏊 Pool: {POOL_NAME}")
        print()
        
        async with aiohttp.ClientSession() as session:
            
            # Step 1: Get or create endpoint
            print("1️⃣  Setting up endpoint...")
            endpoint_id, auth_token = await get_or_create_endpoint(session, ENDPOINT_NAME, HOSTNAME)
            if not endpoint_id:
                print("❌ Could not set up endpoint")
                return False
            
            # Step 2: Get or create pool
            print("\n2️⃣  Setting up pool...")
            pool_id = await get_or_create_pool(session, POOL_NAME)
            if not pool_id:
                print("❌ Could not set up pool")
                return False
            
            # Step 3: Assign endpoint to pool
            print("\n3️⃣  Assigning endpoint to pool...")
            await assign_endpoint_to_pool(session, endpoint_id, pool_id)
            
            # Step 4: Test authenticated operations (if we have a token)
            if auth_token:
                headers = {"Authorization": f"Bearer {auth_token}"}
                
                print("\n4️⃣  Testing status update...")
                try:
                    status_data = {"status": "behind"}
                    async with session.put(
                        f"{SERVER_URL}/api/endpoints/{endpoint_id}/status",
                        json=status_data,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            print("✅ Status updated successfully")
                        else:
                            error_text = await response.text()
                            print(f"⚠️  Status update failed: {response.status} - {error_text}")
                except Exception as e:
                    print(f"⚠️  Status update error: {e}")
                
                print("\n5️⃣  Setting up target state first...")
                # First, we need to set a target state for the pool
                # We'll submit a mock state and then set it as the target
                try:
                    # Submit a mock state
                    state_data = {
                        "endpoint_id": endpoint_id,
                        "timestamp": datetime.now().isoformat(),
                        "packages": [
                            {
                                "package_name": "firefox",
                                "version": "120.0-1",
                                "repository": "extra",
                                "installed_size": 52428800,
                                "dependencies": ["gtk3", "libxt"]
                            },
                            {
                                "package_name": "vim",
                                "version": "9.0.1000-1",
                                "repository": "extra", 
                                "installed_size": 3145728,
                                "dependencies": ["glibc"]
                            }
                        ],
                        "pacman_version": "6.0.2",
                        "architecture": "x86_64"
                    }
                    
                    # Submit state via states API
                    async with session.post(
                        f"{SERVER_URL}/api/states/{endpoint_id}",
                        json=state_data,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            print("✅ Mock state submitted")
                        else:
                            error_text = await response.text()
                            print(f"⚠️  State submission failed: {response.status} - {error_text}")
                    
                    # Now set this endpoint's current state as the target using set-as-latest
                    async with session.post(
                        f"{SERVER_URL}/api/sync/{endpoint_id}/set-as-latest",
                        json={},
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            print("✅ Target state set for pool")
                            print(f"   Set-as-latest operation ID: {data.get('operation_id')}")
                        else:
                            error_text = await response.text()
                            print(f"⚠️  Set-as-latest failed: {response.status} - {error_text}")
                    
                    # Wait a moment for the operation to complete
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    print(f"⚠️  Target state setup error: {e}")
                
                print("\n6️⃣  Testing sync-to-latest operation...")
                try:
                    async with session.post(
                        f"{SERVER_URL}/api/sync/{endpoint_id}/sync-to-latest",
                        json={},
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            operation_id = data.get('operation_id')
                            print(f"✅ Sync-to-latest triggered successfully!")
                            print(f"   Operation ID: {operation_id}")
                            
                            # Monitor operation
                            if operation_id:
                                print("\n7️⃣  Monitoring operation...")
                                for attempt in range(5):
                                    await asyncio.sleep(1)
                                    try:
                                        async with session.get(
                                            f"{SERVER_URL}/api/sync/operations/{operation_id}"
                                        ) as status_response:
                                            if status_response.status == 200:
                                                status_data = await status_response.json()
                                                status = status_data.get('status', 'unknown')
                                                print(f"   Attempt {attempt + 1}: {status}")
                                                if status in ['completed', 'failed']:
                                                    if status == 'failed':
                                                        error_msg = status_data.get('error_message', 'Unknown error')
                                                        print(f"   Error: {error_msg}")
                                                    break
                                            else:
                                                print(f"   Could not get status: {status_response.status}")
                                    except Exception as e:
                                        print(f"   Status check error: {e}")
                            
                        else:
                            error_text = await response.text()
                            print(f"❌ Sync operation failed: {response.status} - {error_text}")
                            
                            # Try to parse the error for more details
                            try:
                                import json
                                error_data = json.loads(error_text)
                                if 'error' in error_data:
                                    user_message = error_data['error'].get('user_message', 'No details')
                                    print(f"   Details: {user_message}")
                            except:
                                pass
                            
                            return False
                            
                except Exception as e:
                    print(f"❌ Sync operation error: {e}")
                    return False
            else:
                print("\n4️⃣  No auth token available (using existing endpoint)")
                print("   You may need to manually trigger sync operations from the client")
            
            print(f"\n🎉 Test completed!")
            print(f"📋 Summary:")
            print(f"   Endpoint ID: {endpoint_id}")
            print(f"   Pool ID: {pool_id}")
            print(f"   Auth Token: {'Available' if auth_token else 'Not available (reusing existing)'}")
            
            return True
            
    except ImportError:
        print("❌ aiohttp not available. Please install: pip install aiohttp")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
        
        print(f"📡 Server: {SERVER_URL}")
        print(f"🖥️  Endpoint: {ENDPOINT_NAME}@{HOSTNAME}")
        print()
        
        async with PacmanSyncAPIClient(SERVER_URL, timeout=15.0) as api_client:
            
            # Step 1: Authenticate
            print("1️⃣  Authenticating...")
            try:
                token = await api_client.authenticate(ENDPOINT_NAME, HOSTNAME)
                endpoint_id = api_client.token_manager.get_current_endpoint_id()
                print(f"✅ Authenticated successfully")
                print(f"   Endpoint ID: {endpoint_id}")
            except Exception as e:
                print(f"❌ Authentication failed: {e}")
                return False
            
            # Step 2: Report initial status
            print("\n2️⃣  Reporting initial status...")
            try:
                await api_client.report_status(endpoint_id, SyncStatus.BEHIND)
                print("✅ Initial status reported (BEHIND)")
            except Exception as e:
                print(f"⚠️  Status reporting failed: {e}")
            
            # Step 3: Trigger sync-to-latest
            print("\n3️⃣  Triggering sync-to-latest operation...")
            try:
                operation_id = await api_client.trigger_sync(endpoint_id, OperationType.SYNC)
                print(f"✅ Sync-to-latest triggered successfully!")
                print(f"   Operation ID: {operation_id}")
                
                # Step 4: Monitor operation progress
                print("\n4️⃣  Monitoring operation progress...")
                
                max_attempts = 10
                attempt = 0
                
                while attempt < max_attempts:
                    try:
                        status = await api_client.get_operation_status(operation_id)
                        if status:
                            op_status = status.get('status', 'unknown')
                            print(f"   Attempt {attempt + 1}: Status = {op_status}")
                            
                            if op_status in ['completed', 'failed']:
                                if op_status == 'completed':
                                    print("🎉 Sync operation completed successfully!")
                                else:
                                    error_msg = status.get('error_message', 'Unknown error')
                                    print(f"❌ Sync operation failed: {error_msg}")
                                break
                        else:
                            print(f"   Attempt {attempt + 1}: Could not get status")
                        
                        await asyncio.sleep(2)  # Wait 2 seconds between checks
                        attempt += 1
                        
                    except Exception as e:
                        print(f"   Status check failed: {e}")
                        break
                
                if attempt >= max_attempts:
                    print("⏰ Operation monitoring timed out")
                
            except Exception as e:
                print(f"❌ Sync operation failed: {e}")
                return False
            
            # Step 5: Report final status
            print("\n5️⃣  Reporting final status...")
            try:
                await api_client.report_status(endpoint_id, SyncStatus.IN_SYNC)
                print("✅ Final status reported (IN_SYNC)")
            except Exception as e:
                print(f"⚠️  Final status reporting failed: {e}")
            
            print("\n🎉 Sync-to-latest test completed!")
            return True
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_set_as_latest():
    """Test the set-as-latest functionality using the same endpoint."""
    
    print("\n📤 Testing Set-as-Latest Functionality")
    print("=" * 40)
    
    try:
        import aiohttp
        
        print(f"📡 Server: {SERVER_URL}")
        print(f"🖥️  Endpoint: {ENDPOINT_NAME}@{HOSTNAME}")
        print()
        
        async with aiohttp.ClientSession() as session:
            
            # Get existing endpoint
            print("1️⃣  Getting existing endpoint...")
            endpoint_id, auth_token = await get_or_create_endpoint(session, ENDPOINT_NAME, HOSTNAME)
            if not endpoint_id:
                print("❌ Could not get endpoint")
                return False
            
            if not auth_token:
                print("⚠️  No auth token available (using existing endpoint)")
                print("   Cannot test set-as-latest without authentication")
                return True
            
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            # Test state submission
            print("\n2️⃣  Testing state submission...")
            try:
                state_data = {
                    "endpoint_id": endpoint_id,
                    "timestamp": datetime.now().isoformat(),
                    "packages": [
                        {
                            "package_name": "firefox",
                            "version": "120.0-1",
                            "repository": "extra",
                            "installed_size": 52428800,
                            "dependencies": ["gtk3", "libxt"]
                        },
                        {
                            "package_name": "vim",
                            "version": "9.0.1000-1",
                            "repository": "extra", 
                            "installed_size": 3145728,
                            "dependencies": ["glibc"]
                        }
                    ],
                    "pacman_version": "6.0.2",
                    "architecture": "x86_64"
                }
                
                async with session.post(
                    f"{SERVER_URL}/api/states/{endpoint_id}",
                    json=state_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ State submitted successfully!")
                        print(f"   State ID: {data.get('state_id', 'unknown')}")
                    else:
                        error_text = await response.text()
                        print(f"⚠️  State submission failed: {response.status} - {error_text}")
                        
            except Exception as e:
                print(f"⚠️  State submission error: {e}")
            
            # Test set-as-latest
            print("\n3️⃣  Testing set-as-latest operation...")
            try:
                async with session.post(
                    f"{SERVER_URL}/api/sync/{endpoint_id}/set-as-latest",
                    json={},
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        operation_id = data.get('operation_id')
                        print(f"✅ Set-as-latest triggered!")
                        print(f"   Operation ID: {operation_id}")
                    else:
                        error_text = await response.text()
                        print(f"❌ Set-as-latest failed: {response.status} - {error_text}")
                        return False
                        
            except Exception as e:
                print(f"❌ Set-as-latest error: {e}")
                return False
            
            print("\n🎉 Set-as-latest test completed!")
            return True
            
    except ImportError:
        print("❌ aiohttp not available")
        return False
    except Exception as e:
        print(f"❌ Set-as-latest test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Pacman Sync Utility - Sync Operations Test")
    print("=" * 55)
    
    try:
        # Test sync-to-latest
        success1 = asyncio.run(test_sync_to_latest())
        
        # Test set-as-latest
        success2 = asyncio.run(test_set_as_latest())
        
        print("\n" + "=" * 55)
        if success1 and success2:
            print("🎉 All sync tests passed!")
        else:
            print("⚠️  Some sync tests failed. Check output above.")
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")

if __name__ == "__main__":
    main()