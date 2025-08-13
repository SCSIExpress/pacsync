#!/usr/bin/env python3
"""
Debug script for Repository Analysis page issues.

This script checks why the Repository Analysis page is not showing
packages or repositories for endpoints.
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


async def check_endpoints():
    """Check what endpoints exist and their pool assignments."""
    print("\n🔍 Checking existing endpoints...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/endpoints") as response:
                if response.status == 200:
                    endpoints = await response.json()
                    print(f"✅ Found {len(endpoints)} endpoints:")
                    
                    for i, endpoint in enumerate(endpoints, 1):
                        print(f"   {i}. {endpoint.get('name', 'Unknown')} ({endpoint.get('id', 'No ID')})")
                        print(f"      Pool: {endpoint.get('pool_id', 'Not assigned')}")
                        print(f"      Status: {endpoint.get('sync_status', 'Unknown')}")
                        print(f"      Last seen: {endpoint.get('last_seen', 'Never')}")
                        print()
                    
                    return endpoints
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to list endpoints: {response.status} - {error_text}")
                    return []
        except Exception as e:
            print(f"❌ Error listing endpoints: {e}")
            return []


async def check_pools():
    """Check what pools exist."""
    print("\n🏊 Checking existing pools...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/pools") as response:
                if response.status == 200:
                    pools = await response.json()
                    print(f"✅ Found {len(pools)} pools:")
                    
                    for i, pool in enumerate(pools, 1):
                        print(f"   {i}. {pool.get('name', 'Unknown')} ({pool.get('id', 'No ID')})")
                        print(f"      Description: {pool.get('description', 'No description')}")
                        print(f"      Endpoints: {len(pool.get('endpoints', []))}")
                        print()
                    
                    return pools
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to list pools: {response.status} - {error_text}")
                    return []
        except Exception as e:
            print(f"❌ Error listing pools: {e}")
            return []


async def check_repository_info_for_endpoint(endpoint_id: str):
    """Check repository information for a specific endpoint."""
    print(f"\n📦 Checking repository info for endpoint: {endpoint_id}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/repositories/endpoint/{endpoint_id}") as response:
                if response.status == 200:
                    repo_info = await response.json()
                    repositories = repo_info.get('repositories', [])
                    
                    print(f"✅ Found {len(repositories)} repositories for endpoint:")
                    
                    for i, repo in enumerate(repositories, 1):
                        print(f"   {i}. {repo.get('repo_name', 'Unknown')} ({repo.get('id', 'No ID')})")
                        print(f"      URL: {repo.get('repo_url', 'No URL')}")
                        print(f"      Mirrors: {len(repo.get('mirrors', []))}")
                        print(f"      Packages: {len(repo.get('packages', []))}")
                        print(f"      Last updated: {repo.get('last_updated', 'Never')}")
                        
                        # Show first few packages
                        packages = repo.get('packages', [])
                        if packages:
                            print(f"      Sample packages:")
                            for pkg in packages[:3]:
                                print(f"        - {pkg.get('name', 'Unknown')} {pkg.get('version', 'No version')}")
                            if len(packages) > 3:
                                print(f"        ... and {len(packages) - 3} more")
                        print()
                    
                    return repositories
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to get repository info: {response.status} - {error_text}")
                    return []
        except Exception as e:
            print(f"❌ Error getting repository info: {e}")
            return []


async def check_pool_analysis(pool_id: str):
    """Check repository analysis for a specific pool."""
    print(f"\n🔬 Checking repository analysis for pool: {pool_id}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/repositories/analysis/{pool_id}") as response:
                if response.status == 200:
                    analysis = await response.json()
                    
                    print(f"✅ Repository analysis found:")
                    print(f"   Pool ID: {analysis.get('pool_id', 'Unknown')}")
                    print(f"   Common packages: {len(analysis.get('common_packages', []))}")
                    print(f"   Excluded packages: {len(analysis.get('excluded_packages', []))}")
                    print(f"   Conflicts: {len(analysis.get('conflicts', []))}")
                    print(f"   Last analyzed: {analysis.get('last_analyzed', 'Never')}")
                    
                    # Show sample common packages
                    common_packages = analysis.get('common_packages', [])
                    if common_packages:
                        print(f"   Sample common packages:")
                        for pkg in common_packages[:5]:
                            print(f"     - {pkg.get('name', 'Unknown')} {pkg.get('version', 'No version')}")
                        if len(common_packages) > 5:
                            print(f"     ... and {len(common_packages) - 5} more")
                    
                    # Show conflicts
                    conflicts = analysis.get('conflicts', [])
                    if conflicts:
                        print(f"   Conflicts:")
                        for conflict in conflicts[:3]:
                            print(f"     - {conflict.get('package_name', 'Unknown')}: {conflict.get('suggested_resolution', 'No resolution')}")
                        if len(conflicts) > 3:
                            print(f"     ... and {len(conflicts) - 3} more")
                    
                    return analysis
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to get repository analysis: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Error getting repository analysis: {e}")
            return None


async def create_test_endpoint_with_repos():
    """Create a test endpoint and submit repository information."""
    print("\n🔧 Creating test endpoint with repository information...")
    
    async with aiohttp.ClientSession() as session:
        # Create endpoint
        endpoint_data = {
            "name": "repo-analysis-test-endpoint",
            "hostname": "test-host"
        }
        
        try:
            async with session.post(f"{SERVER_URL}/api/endpoints/register", json=endpoint_data) as response:
                if response.status == 200:
                    result = await response.json()
                    endpoint_id = result["endpoint"]["id"]
                    auth_token = result["auth_token"]
                    print(f"✅ Created test endpoint: {endpoint_id}")
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to create endpoint: {response.status} - {error_text}")
                    return None, None
        except Exception as e:
            print(f"❌ Error creating endpoint: {e}")
            return None, None
        
        # Submit repository information using the lightweight API
        headers = {"Authorization": f"Bearer {auth_token}"}
        repo_info = {
            "repositories": {
                "core": {
                    "name": "core",
                    "mirrors": [
                        "http://mirror1.example.com/core/os/x86_64",
                        "http://mirror2.example.com/core/os/x86_64"
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
        
        try:
            async with session.post(
                f"{SERVER_URL}/api/endpoints/{endpoint_id}/repository-info",
                json=repo_info,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Submitted repository info: {result.get('repositories_count')} repos, {result.get('total_mirrors')} mirrors")
                    return endpoint_id, auth_token
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to submit repository info: {response.status} - {error_text}")
                    return endpoint_id, auth_token  # Return anyway for further testing
        except Exception as e:
            print(f"❌ Error submitting repository info: {e}")
            return endpoint_id, auth_token


async def create_test_pool_and_assign_endpoint(endpoint_id: str):
    """Create a test pool and assign the endpoint to it."""
    print(f"\n🏊 Creating test pool and assigning endpoint...")
    
    async with aiohttp.ClientSession() as session:
        # Create pool
        import time
        pool_data = {
            "name": f"repo-analysis-test-pool-{int(time.time())}",
            "description": "Test pool for repository analysis debugging"
        }
        
        try:
            async with session.post(f"{SERVER_URL}/api/pools", json=pool_data) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    pool_id = result["id"]
                    print(f"✅ Created test pool: {pool_id}")
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to create pool: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Error creating pool: {e}")
            return None
        
        # Assign endpoint to pool
        try:
            async with session.put(
                f"{SERVER_URL}/api/endpoints/{endpoint_id}/pool",
                params={"pool_id": pool_id}
            ) as response:
                if response.status == 200:
                    print(f"✅ Assigned endpoint to pool")
                    return pool_id
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to assign endpoint to pool: {response.status} - {error_text}")
                    return pool_id  # Return anyway
        except Exception as e:
            print(f"❌ Error assigning endpoint to pool: {e}")
            return pool_id


async def main():
    """Run the repository analysis debug checks."""
    print("🐛 Repository Analysis Debug")
    print("=" * 40)
    
    # Test server health
    if not await test_server_health():
        print("\n❌ Server is not available. Please start the server first.")
        return 1
    
    # Check existing endpoints
    endpoints = await check_endpoints()
    
    # Check existing pools
    pools = await check_pools()
    
    # Check repository info for existing endpoints
    if endpoints:
        print("\n📦 Checking repository info for existing endpoints...")
        for endpoint in endpoints[:3]:  # Check first 3 endpoints
            endpoint_id = endpoint.get('id')
            if endpoint_id:
                repos = await check_repository_info_for_endpoint(endpoint_id)
                if not repos:
                    print(f"   ⚠️  No repository info found for endpoint {endpoint.get('name', 'Unknown')}")
    
    # Check pool analysis for existing pools
    if pools:
        print("\n🔬 Checking repository analysis for existing pools...")
        for pool in pools[:3]:  # Check first 3 pools
            pool_id = pool.get('id')
            if pool_id:
                analysis = await check_pool_analysis(pool_id)
                if not analysis:
                    print(f"   ⚠️  No analysis found for pool {pool.get('name', 'Unknown')}")
    
    # Create test endpoint with repository info
    print("\n🧪 Creating test scenario...")
    endpoint_id, auth_token = await create_test_endpoint_with_repos()
    
    if endpoint_id:
        # Create pool and assign endpoint
        pool_id = await create_test_pool_and_assign_endpoint(endpoint_id)
        
        if pool_id:
            # Check repository info for test endpoint
            await check_repository_info_for_endpoint(endpoint_id)
            
            # Check analysis for test pool
            await check_pool_analysis(pool_id)
    
    print("\n📋 Summary:")
    print("   If repository analysis page is empty, possible causes:")
    print("   1. No endpoints have submitted repository information")
    print("   2. Endpoints are not assigned to pools")
    print("   3. Repository submission API is not working")
    print("   4. Repository analysis is not being triggered")
    print("   5. Web UI is not calling the correct API endpoints")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))