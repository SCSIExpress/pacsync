#!/usr/bin/env python3
"""
Test script to verify client sync functionality.
Run this script to test the authentication and sync operations.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_client_sync():
    """Test client authentication and sync operations."""
    
    print("🧪 Testing Pacman Sync Utility Client")
    print("=" * 50)
    
    try:
        # Import client modules
        from client.api_client import PacmanSyncAPIClient
        from client.auth.token_manager import TokenManager
        from shared.models import SyncStatus, OperationType
        
        # Configuration
        SERVER_URL = "http://localhost:4444"  # Adjust if your server runs on different port
        ENDPOINT_NAME = "test-client"
        HOSTNAME = "test-machine"
        
        print(f"📡 Server URL: {SERVER_URL}")
        print(f"🖥️  Endpoint: {ENDPOINT_NAME}@{HOSTNAME}")
        print()
        
        # Test 1: Create API client
        print("1️⃣  Creating API client...")
        async with PacmanSyncAPIClient(SERVER_URL, timeout=10.0) as api_client:
            print("✅ API client created successfully")
            
            # Test 2: Authentication
            print("\n2️⃣  Testing authentication...")
            try:
                token = await api_client.authenticate(ENDPOINT_NAME, HOSTNAME)
                print(f"✅ Authentication successful")
                print(f"   Token: {token[:20]}..." if token else "   No token received")
                
                endpoint_id = api_client.token_manager.get_current_endpoint_id()
                print(f"   Endpoint ID: {endpoint_id}")
                
            except Exception as e:
                print(f"❌ Authentication failed: {e}")
                return False
            
            # Test 3: Status reporting
            print("\n3️⃣  Testing status reporting...")
            try:
                success = await api_client.report_status(endpoint_id, SyncStatus.IN_SYNC)
                if success:
                    print("✅ Status reported successfully")
                else:
                    print("⚠️  Status reporting returned False")
            except Exception as e:
                print(f"❌ Status reporting failed: {e}")
            
            # Test 4: Trigger sync operation
            print("\n4️⃣  Testing sync operation trigger...")
            try:
                operation_id = await api_client.trigger_sync(endpoint_id, OperationType.SYNC)
                print(f"✅ Sync operation triggered successfully")
                print(f"   Operation ID: {operation_id}")
                
                # Wait a moment and check operation status
                await asyncio.sleep(1)
                
                operation_status = await api_client.get_operation_status(operation_id)
                if operation_status:
                    print(f"   Operation Status: {operation_status.get('status', 'unknown')}")
                else:
                    print("   Could not retrieve operation status")
                    
            except Exception as e:
                print(f"❌ Sync operation failed: {e}")
            
            # Test 5: Test set-as-latest operation
            print("\n5️⃣  Testing set-as-latest operation...")
            try:
                operation_id = await api_client.trigger_sync(endpoint_id, OperationType.SET_LATEST)
                print(f"✅ Set-as-latest operation triggered successfully")
                print(f"   Operation ID: {operation_id}")
            except Exception as e:
                print(f"❌ Set-as-latest operation failed: {e}")
            
            print("\n🎉 Client testing completed!")
            return True
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all client dependencies are installed")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_direct_api_calls():
    """Test direct API calls to verify server endpoints."""
    
    print("\n🔧 Testing Direct API Calls")
    print("=" * 30)
    
    try:
        import aiohttp
        
        SERVER_URL = "http://localhost:4444"
        
        async with aiohttp.ClientSession() as session:
            # Test health endpoint
            print("1️⃣  Testing health endpoint...")
            try:
                async with session.get(f"{SERVER_URL}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Health check passed: {data.get('status', 'unknown')}")
                    else:
                        print(f"⚠️  Health check returned status {response.status}")
            except Exception as e:
                print(f"❌ Health check failed: {e}")
            
            # Test endpoint registration
            print("\n2️⃣  Testing endpoint registration...")
            try:
                registration_data = {
                    "name": "test-direct-client",
                    "hostname": "test-direct-machine"
                }
                
                async with session.post(
                    f"{SERVER_URL}/api/endpoints/register",
                    json=registration_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print("✅ Endpoint registration successful")
                        endpoint_id = data['endpoint']['id']
                        auth_token = data['auth_token']
                        print(f"   Endpoint ID: {endpoint_id}")
                        print(f"   Auth Token: {auth_token[:20]}...")
                        
                        # Test authenticated endpoint
                        print("\n3️⃣  Testing authenticated status update...")
                        headers = {"Authorization": f"Bearer {auth_token}"}
                        status_data = {"status": "in_sync"}
                        
                        async with session.put(
                            f"{SERVER_URL}/api/endpoints/{endpoint_id}/status",
                            json=status_data,
                            headers=headers
                        ) as auth_response:
                            if auth_response.status == 200:
                                print("✅ Authenticated status update successful")
                            else:
                                error_text = await auth_response.text()
                                print(f"❌ Status update failed: {auth_response.status} - {error_text}")
                        
                    else:
                        error_text = await response.text()
                        print(f"❌ Registration failed: {response.status} - {error_text}")
                        
            except Exception as e:
                print(f"❌ Registration test failed: {e}")
                
    except ImportError:
        print("❌ aiohttp not available for direct API testing")
    except Exception as e:
        print(f"❌ Direct API test failed: {e}")

def main():
    """Main test function."""
    print("🚀 Starting Pacman Sync Utility Client Tests")
    print("=" * 60)
    
    # Check if server is likely running
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 4444))
        sock.close()
        
        if result != 0:
            print("⚠️  Warning: Server doesn't appear to be running on localhost:4444")
            print("   Make sure your server is started before running this test")
            print()
    except Exception:
        pass
    
    # Run tests
    try:
        # Run client tests
        success = asyncio.run(test_client_sync())
        
        # Run direct API tests
        asyncio.run(test_direct_api_calls())
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 Tests completed! Check the output above for any issues.")
        else:
            print("⚠️  Some tests failed. Check the error messages above.")
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")

if __name__ == "__main__":
    main()