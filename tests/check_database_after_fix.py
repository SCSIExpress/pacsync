#!/usr/bin/env python3
"""
Check database after the fix attempt.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.database.connection import DatabaseManager


async def main():
    """Check the database state."""
    print("🔍 Checking Database After Fix")
    print("=" * 35)
    
    try:
        # Create database connection
        db_manager = DatabaseManager(database_type="internal")
        await db_manager.initialize()
        
        # Query all repositories
        print("📦 All repositories in database:")
        rows = await db_manager.fetch("""
            SELECT endpoint_id, repo_name, repo_url, 
                   LENGTH(packages) as packages_length,
                   packages
            FROM repositories 
            ORDER BY endpoint_id, repo_name
        """)
        
        for i, row in enumerate(rows, 1):
            endpoint_id = row[0] if isinstance(row, tuple) else row['endpoint_id']
            repo_name = row[1] if isinstance(row, tuple) else row['repo_name']
            repo_url = row[2] if isinstance(row, tuple) else row['repo_url']
            packages_length = row[3] if isinstance(row, tuple) else row['packages_length']
            packages_data = row[4] if isinstance(row, tuple) else row['packages']
            
            print(f"   {i}. Endpoint: {endpoint_id}")
            print(f"      Repo: {repo_name}")
            print(f"      URL: {repo_url}")
            print(f"      Packages length: {packages_length}")
            
            # Try to parse packages
            try:
                import json
                packages = json.loads(packages_data) if packages_data else []
                print(f"      Parsed packages: {len(packages)}")
                if packages:
                    print(f"      Sample package: {packages[0].get('name', 'Unknown')}")
            except Exception as e:
                print(f"      Package parsing error: {e}")
            print()
        
        # Check if dev-client endpoint has repositories
        print("🎯 Checking dev-client specifically:")
        dev_client_rows = await db_manager.fetch("""
            SELECT * FROM repositories 
            WHERE endpoint_id = '9a938477-eaed-48dc-8d18-524c22d7aa2c'
        """)
        
        print(f"   Found {len(dev_client_rows)} repositories for dev-client")
        
        await db_manager.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())