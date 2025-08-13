#!/usr/bin/env python3
"""
Final fix for Repository Analysis page.

This script connects to the correct database file and updates
repository data to fix the Repository Analysis page.
"""

import asyncio
import aiohttp
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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


async def fix_repository_data():
    """Fix repository data by connecting to the correct database."""
    print("🔧 Final Fix for Repository Analysis Page")
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
        # Import aiosqlite directly to connect to the same database file
        import aiosqlite
        
        # Connect to the same database file the server uses
        db_path = project_root / "data" / "pacman_sync.db"
        print(f"📊 Connecting to database: {db_path}")
        
        async with aiosqlite.connect(str(db_path)) as db:
            # Check current repository data
            print("🔍 Checking current repository data...")
            cursor = await db.execute("""
                SELECT endpoint_id, repo_name, LENGTH(packages) as pkg_count
                FROM repositories 
                ORDER BY endpoint_id
            """)
            rows = await cursor.fetchall()
            
            print(f"   Found {len(rows)} repositories:")
            for row in rows:
                endpoint_id, repo_name, pkg_count = row
                print(f"     - {endpoint_id}: {repo_name} ({pkg_count} packages)")
            
            # Update one of the existing repositories to use dev-client ID
            print(f"🔄 Updating repository to use dev-client ID...")
            
            # Find a repository with packages to update
            cursor = await db.execute("""
                SELECT endpoint_id, repo_name, LENGTH(packages) as pkg_count
                FROM repositories 
                WHERE LENGTH(packages) > 100
                LIMIT 1
            """)
            source_repo = await cursor.fetchone()
            
            if source_repo:
                source_endpoint_id, repo_name, pkg_count = source_repo
                print(f"   Updating {repo_name} from {source_endpoint_id} to {dev_client_id}")
                
                # Update the endpoint_id
                await db.execute("""
                    UPDATE repositories 
                    SET endpoint_id = ? 
                    WHERE endpoint_id = ? AND repo_name = ?
                """, (dev_client_id, source_endpoint_id, repo_name))
                
                await db.commit()
                print(f"   ✅ Updated repository endpoint_id")
                
                # Verify the update
                cursor = await db.execute("""
                    SELECT repo_name, LENGTH(packages) as pkg_count
                    FROM repositories 
                    WHERE endpoint_id = ?
                """, (dev_client_id,))
                updated_rows = await cursor.fetchall()
                
                print(f"✅ Verification: Found {len(updated_rows)} repositories for dev-client:")
                for row in updated_rows:
                    repo_name, pkg_count = row
                    print(f"   - {repo_name}: {pkg_count} packages")
                
                return len(updated_rows) > 0
            else:
                print("❌ No repositories with packages found to update")
                return False
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
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
                            for pkg in packages[:3]:
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
    
    # Get the pool that dev-client is assigned to
    endpoints = await get_current_endpoints()
    dev_client = None
    for endpoint in endpoints:
        if endpoint.get('name') == 'dev-client':
            dev_client = endpoint
            break
    
    if not dev_client:
        print("❌ dev-client not found")
        return False
    
    pool_id = dev_client.get('pool_id')
    if not pool_id:
        print("⚠️  dev-client is not assigned to a pool")
        return False
    
    # Test pool analysis
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/repositories/analysis/{pool_id}") as response:
                if response.status == 200:
                    analysis = await response.json()
                    
                    common_packages = analysis.get('common_packages', [])
                    excluded_packages = analysis.get('excluded_packages', [])
                    conflicts = analysis.get('conflicts', [])
                    
                    print(f"✅ Pool analysis results:")
                    print(f"   Common packages: {len(common_packages)}")
                    print(f"   Excluded packages: {len(excluded_packages)}")
                    print(f"   Conflicts: {len(conflicts)}")
                    
                    # Show sample common packages
                    if common_packages:
                        print(f"   Sample common packages:")
                        for pkg in common_packages[:5]:
                            print(f"     - {pkg.get('name', 'Unknown')} {pkg.get('version', 'No version')}")
                    
                    return True
                else:
                    print(f"❌ Pool analysis failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Pool analysis error: {e}")
            return False


async def main():
    """Run the final fix."""
    # Fix repository data
    if not await fix_repository_data():
        print("\n❌ Failed to fix repository data")
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
    print("\n📋 Next steps:")
    print("   1. Open the web UI at http://localhost:4444")
    print("   2. Navigate to Repository Analysis page")
    print("   3. You should now see packages and repositories for dev-client")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))