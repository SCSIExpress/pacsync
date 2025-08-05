#!/usr/bin/env python3
"""
Test script to validate the database schema and migration system.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent / "server"))

from database.connection import DatabaseManager, initialize_database, close_database
from database.migrations import MigrationManager, run_migrations, get_migration_status
from database.schema import create_tables, verify_schema, get_table_info

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_sqlite_database():
    """Test SQLite database functionality."""
    logger.info("Testing SQLite database...")
    
    # Set environment for SQLite
    os.environ["DATABASE_TYPE"] = "internal"
    
    # Clean up any existing test database
    test_db_path = Path("data/pacman_sync.db")
    if test_db_path.exists():
        test_db_path.unlink()
    
    try:
        # Initialize database
        db_manager = await initialize_database()
        
        # Test migration system
        migration_manager = MigrationManager(db_manager)
        status = await migration_manager.get_migration_status()
        logger.info(f"Migration status: {status}")
        
        # Run migrations
        await run_migrations(db_manager)
        
        # Verify schema
        schema_valid = await verify_schema(db_manager)
        logger.info(f"Schema validation: {'PASSED' if schema_valid else 'FAILED'}")
        
        # Get table info
        table_info = await get_table_info(db_manager)
        logger.info(f"Tables created: {list(table_info.keys())}")
        
        # Test basic operations
        await test_basic_operations(db_manager)
        
        await close_database()
        logger.info("SQLite test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"SQLite test failed: {e}")
        await close_database()
        return False


async def test_basic_operations(db_manager: DatabaseManager):
    """Test basic database operations."""
    logger.info("Testing basic database operations...")
    
    # Test pool creation
    pool_id = await db_manager.fetchval(
        f"INSERT INTO pools (name, description) VALUES ({db_manager.get_placeholder()}, {db_manager.get_placeholder(2)}) RETURNING id" if db_manager.database_type == "postgresql" else 
        f"INSERT INTO pools (name, description) VALUES ({db_manager.get_placeholder()}, {db_manager.get_placeholder()}) RETURNING id",
        "test-pool", "Test pool description"
    )
    
    if db_manager.database_type == "internal":
        # For SQLite, we need to get the last inserted row id differently
        pool_id = await db_manager.fetchval("SELECT id FROM pools WHERE name = ?", "test-pool")
    
    logger.info(f"Created pool with ID: {pool_id}")
    
    # Test endpoint creation
    endpoint_id = await db_manager.fetchval(
        f"INSERT INTO endpoints (name, hostname, pool_id) VALUES ({db_manager.get_placeholder()}, {db_manager.get_placeholder(2)}, {db_manager.get_placeholder(3)}) RETURNING id" if db_manager.database_type == "postgresql" else
        f"INSERT INTO endpoints (name, hostname, pool_id) VALUES ({db_manager.get_placeholder()}, {db_manager.get_placeholder()}, {db_manager.get_placeholder()}) RETURNING id",
        "test-endpoint", "test-host", pool_id
    )
    
    if db_manager.database_type == "internal":
        endpoint_id = await db_manager.fetchval("SELECT id FROM endpoints WHERE name = ?", "test-endpoint")
    
    logger.info(f"Created endpoint with ID: {endpoint_id}")
    
    # Test package state creation
    state_data = '{"packages": [{"name": "test-package", "version": "1.0.0"}]}'
    await db_manager.execute(
        f"INSERT INTO package_states (pool_id, endpoint_id, state_data) VALUES ({db_manager.get_placeholder()}, {db_manager.get_placeholder(2)}, {db_manager.get_placeholder(3)})",
        pool_id, endpoint_id, state_data
    )
    
    # Test repository creation
    packages_data = '[{"name": "test-package", "version": "1.0.0"}]'
    await db_manager.execute(
        f"INSERT INTO repositories (endpoint_id, repo_name, packages) VALUES ({db_manager.get_placeholder()}, {db_manager.get_placeholder(2)}, {db_manager.get_placeholder(3)})",
        endpoint_id, "core", packages_data
    )
    
    # Test sync operation creation
    details_data = '{"operation": "sync", "packages_affected": 1}'
    await db_manager.execute(
        f"INSERT INTO sync_operations (pool_id, endpoint_id, operation_type, details) VALUES ({db_manager.get_placeholder()}, {db_manager.get_placeholder(2)}, {db_manager.get_placeholder(3)}, {db_manager.get_placeholder(4)})",
        pool_id, endpoint_id, "sync", details_data
    )
    
    # Verify data was inserted
    pool_count = await db_manager.fetchval("SELECT COUNT(*) FROM pools")
    endpoint_count = await db_manager.fetchval("SELECT COUNT(*) FROM endpoints")
    state_count = await db_manager.fetchval("SELECT COUNT(*) FROM package_states")
    repo_count = await db_manager.fetchval("SELECT COUNT(*) FROM repositories")
    sync_count = await db_manager.fetchval("SELECT COUNT(*) FROM sync_operations")
    
    logger.info(f"Record counts - Pools: {pool_count}, Endpoints: {endpoint_count}, States: {state_count}, Repos: {repo_count}, Syncs: {sync_count}")
    
    if all(count > 0 for count in [pool_count, endpoint_count, state_count, repo_count, sync_count]):
        logger.info("Basic operations test PASSED")
    else:
        raise Exception("Basic operations test FAILED - some records were not created")


async def main():
    """Main test function."""
    logger.info("Starting database schema and migration system tests...")
    
    success = True
    
    # Test SQLite
    if not await test_sqlite_database():
        success = False
    
    # Test PostgreSQL if available (optional)
    if os.getenv("TEST_POSTGRESQL", "").lower() == "true":
        postgres_url = os.getenv("TEST_DATABASE_URL")
        if postgres_url:
            logger.info("Testing PostgreSQL database...")
            os.environ["DATABASE_TYPE"] = "postgresql"
            os.environ["DATABASE_URL"] = postgres_url
            
            try:
                # Similar test for PostgreSQL
                db_manager = await initialize_database()
                migration_manager = MigrationManager(db_manager)
                await run_migrations(db_manager)
                schema_valid = await verify_schema(db_manager)
                await test_basic_operations(db_manager)
                await close_database()
                logger.info("PostgreSQL test completed successfully")
            except Exception as e:
                logger.error(f"PostgreSQL test failed: {e}")
                success = False
                await close_database()
        else:
            logger.warning("PostgreSQL test skipped - TEST_DATABASE_URL not provided")
    
    if success:
        logger.info("All database tests PASSED")
        return 0
    else:
        logger.error("Some database tests FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)