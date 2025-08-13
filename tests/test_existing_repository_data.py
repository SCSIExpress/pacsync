#!/usr/bin/env python3
"""
Test script to check repository data for existing endpoints.

This script tests the repository retrieval API with endpoints that
already have repository data in the database.
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


async def get_existing_endpoints():
    """Get list of existing endpoints."""
    print("\n📋 Getting existing endpoints...")
    
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
                    
                    return endpoints
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to list endpoints: {response.status} - {error_text}")
                    return []
        except Exception as e:
            print(f"❌ Error listing endpoints: {e}")
            return []


async def test_repository_retrieval_for_endpoint(endpoint_id: str, endpoint_name: str):
    """Test repository retrieval for a specific endpoint."""
    print(f"\n📦 Testing repository retrieval for: {endpoint_name} ({endpoint_id})")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/repositories/endpoint/{endpoint_id}") as response:
                if response.status == 200:
                    result = await response.json()
                    repositories = result.get('repositories', [])
                    
                    print(f"✅ Found {len(repositories)} repositories:")
                    
                    for i, repo in enumerate(repositories, 1):
                        print(f"   {i}. {repo.get('repo_name', 'Unknown')}")
                        print(f"      URL: {repo.get('repo_url', 'No URL')}")
                        print(f"      Mirrors: {len(repo.get('mirrors', []))}")
                        print(f"      Packages: {len(repo.get('packages', []))}")
                        
                        # Show first few packages
                        packages = repo.get('packages', [])
                        if packages:
                            print(f"      Sample packages:")
                            for pkg in packages[:3]:
                                print(f"        - {pkg.get('name', 'Unknown')} {pkg.get('version', 'No version')}")
                            if len(packages) > 3:
                                print(f"        ... and {len(packages) - 3} more")
                        print()
                    
                    return len(repositories) > 0
                else:
                    error_text = await response.text()
                    print(f"❌ Repository retrieval failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Error retrieving repositories: {e}")
            return False


async def test_pool_analysis():
    """Test repository analysis for pools."""
    print(f"\n🔬 Testing pool repository analysis...")
    
    async with aiohttp.ClientSession() as session:
        # Get pools first
        try:
            async with session.get(f"{SERVER_URL}/api/pools") as response:
                if response.status == 200:
                    pools = await response.json()
                    print(f"✅ Found {len(pools)} pools")
                    
                    for pool in pools[:3]:  # Test first 3 pools
                        pool_id = pool.get('id')
                        pool_name = pool.get('name', 'Unknown')
                        
                        print(f"\n   Testing analysis for pool: {pool_name} ({pool_id})")
                        
                        try:
                            async with session.get(f"{SERVER_URL}/api/repositories/analysis/{pool_id}") as analysis_response:
                                if analysis_response.status == 200:
                                    analysis = await analysis_response.json()
                                    print(f"   ✅ Analysis found:")
                                    print(f"      Common packages: {len(analysis.get('common_packages', []))}")
                                    print(f"      Excluded packages: {len(analysis.get('excluded_packages', []))}")
                                    print(f"      Conflicts: {len(analysis.get('conflicts', []))}")
                                    
                                    # Show sample common packages
                                    common_packages = analysis.get('common_packages', [])
                                    if common_packages:
                                        print(f"      Sample common packages:")
                                        for pkg in common_packages[:3]:
                                            print(f"        - {pkg.get('name', 'Unknown')} {pkg.get('version', 'No version')}")
                                        if len(common_packages) > 3:
                                            print(f"        ... and {len(common_packages) - 3} more")
                                else:
                                    error_text = await analysis_response.text()
                                    print(f"   ❌ Analysis failed: {analysis_response.status} - {error_text}")
                        except Exception as e:
                            print(f"   ❌ Error getting analysis: {e}")
                    
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to get pools: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Error getting pools: {e}")
            return False


async def main():
    """Run the repository data tests."""
    print("🔍 Testing Existing Repository Data")
    print("=" * 40)
    
    # Test server health
    if not await test_server_health():
        print("\n❌ Server is not available. Please start the server first.")
        return 1
    
    # Get existing endpoints
    endpoints = await get_existing_endpoints()
    if not endpoints:
        print("\n❌ No endpoints found. Cannot test repository retrieval.")
        return 1
    
    # Test repository retrieval for each endpoint
    successful_retrievals = 0
    for endpoint in endpoints:
        endpoint_id = endpoint.get('id')
        endpoint_name = endpoint.get('name', 'Unknown')
        
        if endpoint_id:
            success = await test_repository_retrieval_for_endpoint(endpoint_id, endpoint_name)
            if success:
                successful_retrievals += 1
    
    # Test pool analysis
    await test_pool_analysis()
    
    print(f"\n📋 Summary:")
    print(f"   Total endpoints: {len(endpoints)}")
    print(f"   Endpoints with repositories: {successful_retrievals}")
    
    if successful_retrievals > 0:
        print("✅ Repository retrieval API is working for some endpoints!")
        print("   The Repository Analysis page should show data for these endpoints.")
    else:
        print("❌ No endpoints have retrievable repository data.")
        print("   The Repository Analysis page will be empty.")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))