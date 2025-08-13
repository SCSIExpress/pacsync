#!/usr/bin/env python3
"""
Script to manually fix database schema issues.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from server.database.connection import get_database_manager, initialize_database
from server.database.schema import create_tables, verify_schema, get_table_info, drop_tables

async def main():
    """Fix database schema."""
    print("=== Database Schema Fix ===")
    
    try:
        # Initialize database
        print("Initializing database...")
        db_manager = await initialize_database()
        print(f"Database type: {db_manager.database_type}")
        print(f"Database URL: {db_manager.database_url}")
        
        # Check current schema
        print("\nChecking current schema...")
        schema_valid = await verify_schema(db_manager)
        print(f"Schema valid: {schema_valid}")
        
        # Get table info
        print("\nGetting table info...")
        table_info = await get_table_info(db_manager)
        print(f"Existing tables: {list(table_info.keys())}")
        
        # Drop and recreate tables
        print("\nDropping existing tables...")
        await drop_tables(db_manager)
        
        print("Creating tables...")
        await create_tables(db_manager)
        
        # Verify again
        print("\nVerifying schema after creation...")
        schema_valid = await verify_schema(db_manager)
        print(f"Schema valid: {schema_valid}")
        
        # Get final table info
        table_info = await get_table_info(db_manager)
        print(f"Final tables: {list(table_info.keys())}")
        
        print("\n✓ Database schema fixed successfully!")
        
    except Exception as e:
        print(f"✗ Error fixing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        if 'db_manager' in locals():
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())