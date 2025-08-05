#!/usr/bin/env python3
"""
Test script to validate PostgreSQL schema generation (without requiring a running PostgreSQL server).
"""

import sys
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent / "server"))

from database.connection import DatabaseManager
from database.migrations import MigrationManager
from database.schema import POSTGRESQL_SCHEMA, POSTGRESQL_INDEXES

def test_postgresql_schema_generation():
    """Test that PostgreSQL schema SQL is properly generated."""
    print("Testing PostgreSQL schema generation...")
    
    # Create a mock database manager for PostgreSQL
    db_manager = DatabaseManager("postgresql", "postgresql://test:test@localhost/test")
    
    # Test migration manager initialization
    migration_manager = MigrationManager(db_manager)
    
    print(f"Number of migrations: {len(migration_manager.migrations)}")
    
    # Test that PostgreSQL-specific migrations are included
    migration_versions = [m.version for m in migration_manager.migrations]
    print(f"Migration versions: {migration_versions}")
    
    # Verify PostgreSQL schema contains all required tables
    required_tables = ["pools", "endpoints", "package_states", "repositories", "sync_operations"]
    
    for table in required_tables:
        if table in POSTGRESQL_SCHEMA:
            print(f"✓ PostgreSQL schema for {table} table exists")
        else:
            print(f"✗ PostgreSQL schema for {table} table missing")
            return False
    
    # Verify indexes are defined
    print(f"Number of PostgreSQL indexes: {len(POSTGRESQL_INDEXES)}")
    
    # Test that the initial migration SQL is properly formatted
    initial_migration = migration_manager.migrations[0]
    if "CREATE TABLE IF NOT EXISTS pools" in initial_migration.up_sql:
        print("✓ Initial migration contains pools table creation")
    else:
        print("✗ Initial migration missing pools table creation")
        return False
    
    if "UUID" in initial_migration.up_sql:
        print("✓ PostgreSQL schema uses UUID data type")
    else:
        print("✗ PostgreSQL schema missing UUID data type")
        return False
    
    if "JSONB" in initial_migration.up_sql:
        print("✓ PostgreSQL schema uses JSONB data type")
    else:
        print("✗ PostgreSQL schema missing JSONB data type")
        return False
    
    print("PostgreSQL schema generation test PASSED")
    return True

def test_sqlite_vs_postgresql_differences():
    """Test that SQLite and PostgreSQL schemas have appropriate differences."""
    print("\nTesting SQLite vs PostgreSQL schema differences...")
    
    from database.schema import SQLITE_SCHEMA
    
    # Check UUID vs TEXT differences
    pg_pools = POSTGRESQL_SCHEMA["pools"]
    sqlite_pools = SQLITE_SCHEMA["pools"]
    
    if "UUID" in pg_pools and "TEXT" in sqlite_pools:
        print("✓ PostgreSQL uses UUID, SQLite uses TEXT for IDs")
    else:
        print("✗ ID type differences not properly handled")
        return False
    
    # Check JSONB vs TEXT differences
    if "JSONB" in pg_pools and "TEXT" in sqlite_pools:
        print("✓ PostgreSQL uses JSONB, SQLite uses TEXT for JSON data")
    else:
        print("✗ JSON type differences not properly handled")
        return False
    
    # Check timestamp differences
    if "TIMESTAMP WITH TIME ZONE" in pg_pools and "DATETIME" in sqlite_pools:
        print("✓ PostgreSQL uses TIMESTAMP WITH TIME ZONE, SQLite uses DATETIME")
    else:
        print("✗ Timestamp type differences not properly handled")
        return False
    
    print("Schema differences test PASSED")
    return True

def main():
    """Main test function."""
    print("Starting PostgreSQL schema validation tests...")
    
    success = True
    
    if not test_postgresql_schema_generation():
        success = False
    
    if not test_sqlite_vs_postgresql_differences():
        success = False
    
    if success:
        print("\nAll PostgreSQL schema tests PASSED")
        return 0
    else:
        print("\nSome PostgreSQL schema tests FAILED")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)