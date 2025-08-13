#!/usr/bin/env python3
"""
Debug script to check endpoint ID mismatches.

This script compares the endpoint IDs in the repositories table
with the current endpoints to find mismatches.
"""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.database.connection import DatabaseManager

SERVER_URL = "http://localhost:4444"


async def get_current_endpoints():
    """Get current endpoints from API."""
    print("📋 Getting current endpoints from API...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{SERVER_URL}/api/endpoints") as response:
                if response.status == 200:
                    endpoints = await response.json()
                    print(f"✅ Found {len(endpoints)} current endpoints:")
                    
                    endpoint_ids = []
                    for endpoint in endpoints:
                        endpoint_id = endpoint.get('id')
                        endpoint_name = endpoint.get('name', 'Unknown')
                        endpoint_ids.append(endpoint_id)
                        print(f"   - {endpoint_name}: {endpoint_id}")
                    
                    return endpoint_ids
                else:
                    print(f"❌ Failed to get endpoints: {response.status}")
                    return []
        except Exception as e:
            print(f"❌ Error getting endpoints: {e}")
            return []


async def get_repository_endpoint_ids():
    """Get endpoint IDs from repositories table."""
    print("\n📦 Getting endpoint IDs from repositories table...")
    
    try:
        # Create database connection
        db_manager = DatabaseManager(database_type="internal")
        await db_manager.initialize()
        
        # Query repository endpoint IDs
        rows = await db_manager.fetch("SELECT DISTINCT endpoint_id FROM repositories")
        
        endpoint_ids = []
        for row in rows:
            endpoint_id = row[0] if isinstance(row, tuple) else row['endpoint_id']
            endpoint_ids.append(endpoint_id)
        
        print(f"✅ Found {len(endpoint_ids)} endpoint IDs in repositories:")
        for endpoint_id in endpoint_ids:
            print(f"   - {endpoint_id}")
        
        await db_manager.close()
        return endpoint_ids
        
    except Exception as e:
        print(f"❌ Error querying repositories: {e}")
        return []


async def get_repository_details():
    """Get detailed repository information."""
    print("\n📊 Getting detailed repository information...")
    
    try:
        # Create database connection
        db_manager = DatabaseManager(database_type="internal")
        await db_manager.initialize()
        
        # Query repository details
        rows = await db_manager.fetch("""
            SELECT endpoint_id, repo_name, repo_url, mirrors, 
                   LENGTH(packages) as packages_length
            FROM repositories 
            ORDER BY endpoint_id, repo_name
        """)
        
        print(f"✅ Found {len(rows)} repositories:")
        for row in rows:
            endpoint_id = row[0] if isinstance(row, tuple) else row['endpoint_id']
            repo_name = row[1] if isinstance(row, tuple) else row['repo_name']
            repo_url = row[2] if isinstance(row, tuple) else row['repo_url']
            mirrors = row[3] if isinstance(row, tuple) else row['mirrors']
            packages_length = row[4] if isinstance(row, tuple) else row['packages_length']
            
            print(f"   - Endpoint: {endpoint_id}")
            print(f"     Repo: {repo_name}")
            print(f"     URL: {repo_url}")
            print(f"     Mirrors: {mirrors}")
            print(f"     Packages data length: {packages_length}")
            print()
        
        await db_manager.close()
        return rows
        
    except Exception as e:
        print(f"❌ Error querying repository details: {e}")
        return []


async def main():
    """Run the endpoint mismatch debug."""
    print("🔍 Debugging Endpoint ID Mismatches")
    print("=" * 45)
    
    # Get current endpoints
    current_endpoints = await get_current_endpoints()
    
    # Get repository endpoint IDs
    repo_endpoints = await get_repository_endpoint_ids()
    
    # Get detailed repository info
    await get_repository_details()
    
    # Compare endpoint IDs
    print("\n🔍 Comparing endpoint IDs...")
    
    current_set = set(current_endpoints)
    repo_set = set(repo_endpoints)
    
    # Find mismatches
    only_in_current = current_set - repo_set
    only_in_repos = repo_set - current_set
    in_both = current_set & repo_set
    
    print(f"   Endpoints only in current API: {len(only_in_current)}")
    for endpoint_id in only_in_current:
        print(f"     - {endpoint_id}")
    
    print(f"   Endpoints only in repositories: {len(only_in_repos)}")
    for endpoint_id in only_in_repos:
        print(f"     - {endpoint_id}")
    
    print(f"   Endpoints in both: {len(in_both)}")
    for endpoint_id in in_both:
        print(f"     - {endpoint_id}")
    
    print(f"\n📋 Summary:")
    if len(in_both) > 0:
        print(f"✅ {len(in_both)} endpoints have both current registration and repository data")
        print("   These should show up in the Repository Analysis page")
    else:
        print("❌ No endpoints have both current registration and repository data")
        print("   This explains why the Repository Analysis page is empty")
    
    if len(only_in_repos) > 0:
        print(f"⚠️  {len(only_in_repos)} endpoints have repository data but are no longer registered")
        print("   This is old data from deleted/recreated endpoints")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))