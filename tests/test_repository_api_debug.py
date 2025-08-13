#!/usr/bin/env python3
"""
Debug script for repository API issues.

This script tests the repository API endpoints to see where the data is getting lost.
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


async def create_test_endpoint():
    """Create a test endpoint."""
    print("\n🔧 Creating test endpoint...")
    
    async with aiohttp.ClientSession() as session:
        endpoint_data = {
            "name": "api-debug-test-endpoint",
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


async def test_old_repository_submission(endpoint_id: str, auth_token: str):
    """Test the old repository submission API with packages."""
    print(f"\n📦 Testing OLD repository submission API...")
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Submit using old format (with packages)
        old_format_data = {
            "repositories": [
                {
                    "repo_name": "core",
                    "repo_url": "http://old-test.example.com/core/os/x86_64",
                    "packages": [
                        {
                            "name": "test-package-old",
                            "version": "1.0.0",
                            "repository": "core",
                            "architecture": "x86_64",
                            "description": "Test package for old API"
                        }
                    ]
                }
            ]
        }
        
        try:
            async with session.post(
                f"{SERVER_URL}/api/endpoints/{endpoint_id}/repositories",
                json=old_format_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    print(f"✅ Old repository submission successful")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Old repository submission failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Error with old repository submission: {e}")
            return False


async def test_new_repository_submission(endpoint_id: str, auth_token: str):
    """Test the new lightweight repository submission API."""
    print(f"\n📦 Testing NEW repository submission API...")
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Submit using new lightweight format
        new_format_data = {
            "repositories": {
                "extra": {
                    "name": "extra",
                    "mirrors": [
                        "http://new-test1.example.com/extra/os/x86_64",
                        "http://new-test2.example.com/extra/os/x86_64"
                    ],
                    "primary_url": "http://new-test1.example.com/extra/os/x86_64",
                    "architecture": "x86_64",
                    "endpoint_id": endpoint_id
                }
            }
        }
        
        try:
            async with session.post(
                f"{SERVER_URL}/api/endpoints/{endpoint_id}/repository-info",
                json=new_format_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ New repository submission successful: {result.get('repositories_count')} repos, {result.get('total_mirrors')} mirrors")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ New repository submission failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Error with new repository submission: {e}")
            return False


async def test_repository_retrieval(endpoint_id: str):
    """Test retrieving repository information."""
    print(f"\n🔍 Testing repository retrieval...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/repositories/endpoint/{endpoint_id}") as response:
                if response.status == 200:
                    result = await response.json()
                    repositories = result.get('repositories', [])
                    print(f"✅ Repository retrieval successful: {len(repositories)} repositories found")
                    
                    for i, repo in enumerate(repositories, 1):
                        print(f"   {i}. {repo.get('repo_name', 'Unknown')}")
                        print(f"      URL: {repo.get('repo_url', 'No URL')}")
                        print(f"      Mirrors: {repo.get('mirrors', [])}")
                        print(f"      Packages: {len(repo.get('packages', []))}")
                        
                        # Show first package if any
                        packages = repo.get('packages', [])
                        if packages:
                            pkg = packages[0]
                            print(f"      Sample package: {pkg.get('name', 'Unknown')} {pkg.get('version', 'No version')}")
                        print()
                    
                    return repositories
                else:
                    error_text = await response.text()
                    print(f"❌ Repository retrieval failed: {response.status} - {error_text}")
                    return []
        except Exception as e:
            print(f"❌ Error retrieving repositories: {e}")
            return []


async def test_endpoint_listing(endpoint_id: str):
    """Test if the endpoint appears in the endpoint list."""
    print(f"\n📋 Testing endpoint listing...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/endpoints") as response:
                if response.status == 200:
                    endpoints = await response.json()
                    print(f"✅ Found {len(endpoints)} total endpoints")
                    
                    # Find our test endpoint
                    test_endpoint = None
                    for endpoint in endpoints:
                        if endpoint.get('id') == endpoint_id:
                            test_endpoint = endpoint
                            break
                    
                    if test_endpoint:
                        print(f"✅ Test endpoint found in list:")
                        print(f"   Name: {test_endpoint.get('name', 'Unknown')}")
                        print(f"   ID: {test_endpoint.get('id', 'No ID')}")
                        print(f"   Pool: {test_endpoint.get('pool_id', 'Not assigned')}")
                        print(f"   Status: {test_endpoint.get('sync_status', 'Unknown')}")
                        return test_endpoint
                    else:
                        print(f"❌ Test endpoint not found in list")
                        return None
                else:
                    error_text = await response.text()
                    print(f"❌ Endpoint listing failed: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Error listing endpoints: {e}")
            return None


async def main():
    """Run the repository API debug tests."""
    print("🐛 Repository API Debug")
    print("=" * 30)
    
    # Test server health
    if not await test_server_health():
        print("\n❌ Server is not available. Please start the server first.")
        return 1
    
    # Create test endpoint
    endpoint_id, auth_token = await create_test_endpoint()
    if not endpoint_id or not auth_token:
        print("\n❌ Failed to create test endpoint. Cannot continue.")
        return 1
    
    # Test endpoint listing
    endpoint_info = await test_endpoint_listing(endpoint_id)
    
    # Test old repository submission
    old_success = await test_old_repository_submission(endpoint_id, auth_token)
    
    # Test repository retrieval after old submission
    if old_success:
        print(f"\n🔍 Checking repositories after OLD submission...")
        repos_after_old = await test_repository_retrieval(endpoint_id)
        print(f"   Found {len(repos_after_old)} repositories after old submission")
    
    # Test new repository submission
    new_success = await test_new_repository_submission(endpoint_id, auth_token)
    
    # Test repository retrieval after new submission
    if new_success:
        print(f"\n🔍 Checking repositories after NEW submission...")
        repos_after_new = await test_repository_retrieval(endpoint_id)
        print(f"   Found {len(repos_after_new)} repositories after new submission")
    
    # Final repository check
    print(f"\n🔍 Final repository check...")
    final_repos = await test_repository_retrieval(endpoint_id)
    
    print("\n📋 Summary:")
    print(f"   Endpoint created: {'✅' if endpoint_id else '❌'}")
    print(f"   Endpoint in list: {'✅' if endpoint_info else '❌'}")
    print(f"   Old API works: {'✅' if old_success else '❌'}")
    print(f"   New API works: {'✅' if new_success else '❌'}")
    print(f"   Final repo count: {len(final_repos)}")
    
    if len(final_repos) == 0:
        print("\n💡 Possible issues:")
        print("   1. Repository data is not being stored in database")
        print("   2. Database schema is missing mirrors column")
        print("   3. Repository ORM has serialization issues")
        print("   4. Repository retrieval API has bugs")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))