#!/usr/bin/env python3
"""
Simple fix for Repository Analysis page.

This script updates one of the existing repository entries
to use a current endpoint ID.
"""

import asyncio
import aiohttp
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.database.connection import DatabaseManager

SERVER_URL = "http://localhost:4444"


async def get_current_endpoints():
    """Get current endpoints."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/endpoints") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return []
        except Exception as e:
            print(f"Error getting endpoints: {e}")
            return []


async def update_repository_endpoint():
    """Update an existing repository to use a current endpoint ID."""
    print("🔧 Simple Fix for Repository Analysis Page")
    print("=" * 45)
    
    # Get current endpoints
    print("📋 Getting current endpoints...")
    endpoints = await get_current_endpoints()
    if not endpoints:
        print("❌ No current endpoints found")
        return False
    
    # Find dev-client endpoint
    dev_client = None
    for endpoint in endpoints:
        if endpoint.get('name') == 'dev-client':
            dev_client = endpoint
            break
    
    if not dev_client:
        print("❌ dev-client endpoint not found")
        return False
    
    dev_client_id = dev_client.get('id')
    print(f"✅ Found dev-client: {dev_client_id}")
    
    try:
        # Connect to database
        print("📊 Connecting to database...")
        db_manager = DatabaseManager(database_type="internal")
        await db_manager.initialize()
        
        # Update one of the existing repositories to use dev-client ID
        print("🔄 Updating repository endpoint_id...")
        
        # Use the first repository (ui-endpoint-1) and change it to dev-client
        result = await db_manager.execute("""
            UPDATE repositories 
            SET endpoint_id = ? 
            WHERE endpoint_id = 'ui-endpoint-1'
        """, dev_client_id)
        
        print("✅ Repository endpoint_id updated")
        
        # Verify the update
        print("🔍 Verifying update...")
        rows = await db_manager.fetch("""
            SELECT repo_name, LENGTH(packages) as pkg_count
            FROM repositories 
            WHERE endpoint_id = ?
        """, dev_client_id)
        
        print(f"✅ Found {len(rows)} repositories for dev-client:")
        for row in rows:
            repo_name = row[0] if isinstance(row, tuple) else row['repo_name']
            pkg_count = row[1] if isinstance(row, tuple) else row['pkg_count']
            print(f"   - {repo_name}: {pkg_count} packages")
        
        await db_manager.close()
        return len(rows) > 0
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


async def test_api_after_fix():
    """Test the repository API after the fix."""
    print("\n🧪 Testing repository API after fix...")
    
    # Get dev-client endpoint
    endpoints = await get_current_endpoints()
    dev_client = None
    for endpoint in endpoints:
        if endpoint.get('name') == 'dev-client':
            dev_client = endpoint
            break
    
    if not dev_client:
        print("❌ dev-client not found")
        return False
    
    dev_client_id = dev_client.get('id')
    
    # Test repository retrieval
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/repositories/endpoint/{dev_client_id}") as response:
                if response.status == 200:
                    result = await response.json()
                    repositories = result.get('repositories', [])
                    
                    print(f"✅ API returned {len(repositories)} repositories:")
                    
                    total_packages = 0
                    for repo in repositories:
                        repo_name = repo.get('repo_name', 'Unknown')
                        packages = repo.get('packages', [])
                        total_packages += len(packages)
                        print(f"   - {repo_name}: {len(packages)} packages")
                        
                        # Show sample packages
                        if packages:
                            for pkg in packages[:2]:
                                print(f"     * {pkg.get('name', 'Unknown')} {pkg.get('version', 'No version')}")
                    
                    print(f"📦 Total packages: {total_packages}")
                    return len(repositories) > 0
                else:
                    print(f"❌ API call failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ API test error: {e}")
            return False


async def test_pool_analysis():
    """Test pool analysis after the fix."""
    print("\n🔬 Testing pool analysis...")
    
    # Get pools
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/pools") as response:
                if response.status == 200:
                    pools = await response.json()
                    
                    if pools:
                        pool = pools[0]  # Test first pool
                        pool_id = pool.get('id')
                        pool_name = pool.get('name', 'Unknown')
                        
                        print(f"🔍 Testing analysis for pool: {pool_name}")
                        
                        async with session.get(f"{SERVER_URL}/api/repositories/analysis/{pool_id}") as analysis_response:
                            if analysis_response.status == 200:
                                analysis = await analysis_response.json()
                                
                                common_packages = analysis.get('common_packages', [])
                                excluded_packages = analysis.get('excluded_packages', [])
                                conflicts = analysis.get('conflicts', [])
                                
                                print(f"✅ Analysis results:")
                                print(f"   Common packages: {len(common_packages)}")
                                print(f"   Excluded packages: {len(excluded_packages)}")
                                print(f"   Conflicts: {len(conflicts)}")
                                
                                # Show sample common packages
                                if common_packages:
                                    print(f"   Sample common packages:")
                                    for pkg in common_packages[:3]:
                                        print(f"     - {pkg.get('name', 'Unknown')} {pkg.get('version', 'No version')}")
                                
                                return True
                            else:
                                print(f"❌ Analysis failed: {analysis_response.status}")
                                return False
                    else:
                        print("❌ No pools found")
                        return False
                else:
                    print(f"❌ Failed to get pools: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Pool analysis error: {e}")
            return False


async def main():
    """Run the simple fix."""
    # Update repository endpoint
    if not await update_repository_endpoint():
        print("\n❌ Failed to update repository endpoint")
        return 1
    
    # Test API after fix
    if not await test_api_after_fix():
        print("\n❌ API test failed after fix")
        return 1
    
    # Test pool analysis
    await test_pool_analysis()
    
    print("\n🎉 Repository Analysis page fix completed!")
    print("   ✅ Repository data is now linked to current endpoint")
    print("   ✅ Repository API is returning data")
    print("   ✅ Repository Analysis page should now show packages and repositories")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))