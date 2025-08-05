#!/usr/bin/env python3
"""
Test script to validate environment variable configuration for database connections.
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent / "server"))

from database.connection import DatabaseManager, get_database_manager, initialize_database, close_database

async def test_environment_variable_config():
    """Test that environment variables properly configure database connections."""
    print("Testing environment variable configuration...")
    
    # Test 1: Default internal database
    print("\n1. Testing default internal database configuration...")
    os.environ.pop("DATABASE_TYPE", None)
    os.environ.pop("DATABASE_URL", None)
    
    db_manager = DatabaseManager()
    assert db_manager.database_type == "internal", f"Expected 'internal', got '{db_manager.database_type}'"
    print("✓ Default database type is 'internal'")
    
    # Test 2: Explicit internal database
    print("\n2. Testing explicit internal database configuration...")
    os.environ["DATABASE_TYPE"] = "internal"
    
    db_manager = DatabaseManager(
        database_type=os.getenv("DATABASE_TYPE", "internal")
    )
    assert db_manager.database_type == "internal", f"Expected 'internal', got '{db_manager.database_type}'"
    print("✓ Explicit internal database type works")
    
    # Test 3: PostgreSQL configuration
    print("\n3. Testing PostgreSQL configuration...")
    os.environ["DATABASE_TYPE"] = "postgresql"
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/testdb"
    
    db_manager = DatabaseManager(
        database_type=os.getenv("DATABASE_TYPE"),
        database_url=os.getenv("DATABASE_URL")
    )
    assert db_manager.database_type == "postgresql", f"Expected 'postgresql', got '{db_manager.database_type}'"
    assert db_manager.database_url == "postgresql://user:pass@localhost:5432/testdb"
    print("✓ PostgreSQL configuration works")
    
    # Test 4: Global database manager
    print("\n4. Testing global database manager...")
    os.environ["DATABASE_TYPE"] = "internal"
    os.environ.pop("DATABASE_URL", None)
    
    # Reset global manager
    import database.connection
    database.connection._db_manager = None
    
    global_manager = get_database_manager()
    assert global_manager.database_type == "internal"
    print("✓ Global database manager uses environment variables")
    
    # Test 5: SQLite path configuration
    print("\n5. Testing SQLite path configuration...")
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a custom data directory
        custom_data_dir = Path(temp_dir) / "custom_data"
        custom_data_dir.mkdir()
        
        # Change to temp directory to test relative path handling
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            db_manager = DatabaseManager("internal")
            await db_manager.initialize()
            
            # Check that database file is created in data/ subdirectory
            expected_path = Path("data/pacman_sync.db")
            assert expected_path.exists(), f"Database file not created at {expected_path}"
            print(f"✓ SQLite database created at {expected_path.absolute()}")
            
            await db_manager.close()
            
        finally:
            os.chdir(original_cwd)
    
    print("\nEnvironment variable configuration test PASSED")
    return True

async def test_database_type_validation():
    """Test that invalid database types are properly rejected."""
    print("\nTesting database type validation...")
    
    # Test invalid database type
    try:
        db_manager = DatabaseManager("invalid_type")
        await db_manager.initialize()
        print("✗ Invalid database type should have been rejected")
        return False
    except ValueError as e:
        if "Unsupported database type" in str(e):
            print("✓ Invalid database type properly rejected")
        else:
            print(f"✗ Unexpected error: {e}")
            return False
    
    # Test PostgreSQL without URL
    try:
        db_manager = DatabaseManager("postgresql", None)
        await db_manager.initialize()
        print("✗ PostgreSQL without URL should have been rejected")
        return False
    except ValueError as e:
        if "DATABASE_URL is required" in str(e):
            print("✓ PostgreSQL without URL properly rejected")
        else:
            print(f"✗ Unexpected error: {e}")
            return False
    
    print("Database type validation test PASSED")
    return True

async def test_placeholder_methods():
    """Test database-specific placeholder methods."""
    print("\nTesting database-specific placeholder methods...")
    
    # Test PostgreSQL placeholders
    pg_manager = DatabaseManager("postgresql", "postgresql://test:test@localhost/test")
    assert pg_manager.get_placeholder(1) == "$1"
    assert pg_manager.get_placeholder(5) == "$5"
    assert pg_manager.get_returning_clause() == "RETURNING *"
    print("✓ PostgreSQL placeholders work correctly")
    
    # Test SQLite placeholders
    sqlite_manager = DatabaseManager("internal")
    assert sqlite_manager.get_placeholder(1) == "?"
    assert sqlite_manager.get_placeholder(5) == "?"
    assert sqlite_manager.get_returning_clause() == ""
    print("✓ SQLite placeholders work correctly")
    
    print("Placeholder methods test PASSED")
    return True

async def main():
    """Main test function."""
    print("Starting environment variable configuration tests...")
    
    success = True
    
    if not await test_environment_variable_config():
        success = False
    
    if not await test_database_type_validation():
        success = False
    
    if not await test_placeholder_methods():
        success = False
    
    if success:
        print("\nAll environment configuration tests PASSED")
        return 0
    else:
        print("\nSome environment configuration tests FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)