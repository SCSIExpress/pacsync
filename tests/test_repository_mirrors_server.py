#!/usr/bin/env python3
"""
Test script for server-side repository mirror support.

This script tests the server's ability to handle repository information
with multiple mirrors from the updated client.
"""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

SERVER_URL = "http://localhost:4444"


async def test_repository_info_submission():
    """Test submitting repository info with mirrors."""
    print("🧪 Testing repository info submission with mirrors...")
    
    async with aiohttp.ClientSession() as session:
        # First, create an endpoint
        endpoint_data = {
            "name": "test-mirrors-endpoint",
            "hostname": "test-host"
        }
        
        async with session.post(f"{SERVER_URL}/api/endpoints", json=endpoint_data) as response:
            if response.status != 200:
                print(f"❌ Failed to create endpoint: {response.status}")
                return False
            
            result = await response.json()
            endpoint_id = result["id"]
            auth_token = result["auth_token"]
            print(f"✅ Created endpoint: {endpoint_id}")
        
        # Submit repository info with mirrors
        headers = {"Authorization": f"Bearer {auth_token}"}
        repo_info = {
            "repositories": {
                "core": {
                    "name": "core",
                    "mirrors": [
                        "http://mirror1.example.com/core/os/x86_64",
                        "http://mirror2.example.com/core/os/x86_64",
                        "https://mirror3.example.com/core/os/x86_64"
                    ],
                    "primary_url": "http://mirror1.example.com/core/os/x86_64",
                    "architecture": "x86_64",
                    "endpoint_id": endpoint_id
                },
                "extra": {
                    "name": "extra",
                    "mirrors": [
                        "http://mirror1.example.com/extra/os/x86_64",
                        "http://mirror2.example.com/extra/os/x86_64"
                    ],
                    "primary_url": "http://mirror1.example.com/extra/os/x86_64",
                    "architecture": "x86_64",
                    "endpoint_id": endpoint_id
                }
            }
        }
        
        async with session.post(
            f"{SERVER_URL}/api/endpoints/{endpoint_id}/repository-info",
            json=repo_info,
            headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Repository info submitted: {result.get('repositories_count')} repos, {result.get('total_mirrors')} mirrors")
                return True
            else:
                error_text = await response.text()
                print(f"❌ Failed to submit repository info: {response.status} - {error_text}")
                return False


async def test_repository_info_retrieval():
    """Test retrieving repository info with mirrors."""
    print("\n🔍 Testing repository info retrieval...")
    
    async with aiohttp.ClientSession() as session:
        # Create endpoint and submit data first
        endpoint_data = {
            "name": "test-retrieval-endpoint",
            "hostname": "test-host-2"
        }
        
        async with session.post(f"{SERVER_URL}/api/endpoints", json=endpoint_data) as response:
            if response.status != 200:
                print(f"❌ Failed to create endpoint: {response.status}")
                return False
            
            result = await response.json()
            endpoint_id = result["id"]
            auth_token = result["auth_token"]
        
        # Submit repository info
        headers = {"Authorization": f"Bearer {auth_token}"}
        repo_info = {
            "repositories": {
                "multilib": {
                    "name": "multilib",
                    "mirrors": [
                        "http://mirror1.example.com/multilib/os/x86_64",
                        "http://mirror2.example.com/multilib/os/x86_64",
                        "http://mirror3.example.com/multilib/os/x86_64",
                        "https://secure-mirror.example.com/multilib/os/x86_64"
                    ],
                    "primary_url": "http://mirror1.example.com/multilib/os/x86_64",
                    "architecture": "x86_64",
                    "endpoint_id": endpoint_id
                }
            }
        }
        
        await session.post(
            f"{SERVER_URL}/api/endpoints/{endpoint_id}/repository-info",
            json=repo_info,
            headers=headers
        )
        
        # Retrieve repository info
        async with session.get(
            f"{SERVER_URL}/api/repositories/endpoint/{endpoint_id}"
        ) as response:
            if response.status == 200:
                result = await response.json()
                repositories = result.get("repositories", [])
                
                if repositories:
                    repo = repositories[0]
                    mirrors = repo.get("mirrors", [])
                    print(f"✅ Retrieved repository: {repo['repo_name']}")
                    print(f"   Primary URL: {repo['repo_url']}")
                    print(f"   Mirrors: {len(mirrors)} total")
                    for i, mirror in enumerate(mirrors[:3]):
                        print(f"     {i+1}. {mirror}")
                    if len(mirrors) > 3:
                        print(f"     ... and {len(mirrors) - 3} more")
                    return True
                else:
                    print("❌ No repositories found")
                    return False
            else:
                error_text = await response.text()
                print(f"❌ Failed to retrieve repository info: {response.status} - {error_text}")
                return False


async def test_backward_compatibility():
    """Test that old repository submission still works."""
    print("\n🔄 Testing backward compatibility...")
    
    async with aiohttp.ClientSession() as session:
        # Create endpoint
        endpoint_data = {
            "name": "test-compat-endpoint",
            "hostname": "test-host-3"
        }
        
        async with session.post(f"{SERVER_URL}/api/endpoints", json=endpoint_data) as response:
            if response.status != 200:
                print(f"❌ Failed to create endpoint: {response.status}")
                return False
            
            result = await response.json()
            endpoint_id = result["id"]
            auth_token = result["auth_token"]
        
        # Submit using old format (with packages)
        headers = {"Authorization": f"Bearer {auth_token}"}
        old_format_data = {
            "repositories": [
                {
                    "repo_name": "community",
                    "repo_url": "http://old-mirror.example.com/community/os/x86_64",
                    "packages": [
                        {
                            "name": "test-package",
                            "version": "1.0.0",
                            "repository": "community",
                            "architecture": "x86_64",
                            "description": "Test package"
                        }
                    ]
                }
            ]
        }
        
        async with session.post(
            f"{SERVER_URL}/api/endpoints/{endpoint_id}/repositories",
            json=old_format_data,
            headers=headers
        ) as response:
            if response.status == 200:
                print("✅ Old format submission still works")
                return True
            else:
                error_text = await response.text()
                print(f"❌ Old format submission failed: {response.status} - {error_text}")
                return False


async def test_server_health():
    """Test if server is running and healthy."""
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


async def main():
    """Run all tests."""
    print("🧪 Repository Mirrors Server Test")
    print("=" * 50)
    
    # Check server health first
    if not await test_server_health():
        print("\n❌ Server is not available. Please start the server first.")
        return 1
    
    tests = [
        test_repository_info_submission,
        test_repository_info_retrieval,
        test_backward_compatibility
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Server-side mirror support is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))