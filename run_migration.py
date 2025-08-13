#!/usr/bin/env python3
"""
Script to run database migrations for the Pacman Sync Utility.

This script applies pending migrations to add the mirrors column
to the repositories table.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from server.database.connection import DatabaseManager
from server.database.migrations import MigrationManager


async def main():
    """Run database migrations."""
    print("🔄 Running Database Migrations")
    print("=" * 40)
    
    try:
        # Create database manager
        print("📊 Connecting to database...")
        db_manager = DatabaseManager(database_type="internal")
        await db_manager.initialize()
        
        # Create migration manager
        migration_manager = MigrationManager(db_manager)
        
        # Get applied migrations
        print("🔍 Checking applied migrations...")
        applied = await migration_manager.get_applied_migrations()
        print(f"   Applied migrations: {applied}")
        
        # Get pending migrations
        print("📋 Checking pending migrations...")
        pending = await migration_manager.get_pending_migrations()
        print(f"   Pending migrations: {len(pending)}")
        
        if not pending:
            print("✅ No pending migrations to apply")
            await db_manager.close()
            return 0
        
        # Apply pending migrations
        print("🚀 Applying pending migrations...")
        for migration in pending:
            print(f"   Applying {migration.version}: {migration.description}")
            success = await migration_manager.apply_migration(migration)
            if success:
                print(f"   ✅ Migration {migration.version} applied successfully")
            else:
                print(f"   ❌ Migration {migration.version} failed")
                await db_manager.close()
                return 1
        
        print("🎉 All migrations applied successfully!")
        
        # Verify the mirrors column exists
        print("🔍 Verifying mirrors column...")
        try:
            # Try to query the mirrors column
            result = await db_manager.fetch("SELECT id, mirrors FROM repositories LIMIT 1")
            print("✅ Mirrors column exists and is accessible")
        except Exception as e:
            print(f"❌ Error accessing mirrors column: {e}")
            await db_manager.close()
            return 1
        
        await db_manager.close()
        return 0
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))