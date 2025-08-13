"""
Database schema definitions for the Pacman Sync Utility.

This module contains SQL schema definitions for both PostgreSQL and SQLite,
with functions to create and drop tables.
"""

import logging
from typing import List
from .connection import DatabaseManager

logger = logging.getLogger(__name__)

# PostgreSQL schema definitions
POSTGRESQL_SCHEMA = {
    "pools": """
        CREATE TABLE IF NOT EXISTS pools (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            target_state_id UUID,
            sync_policy JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """,
    
    "endpoints": """
        CREATE TABLE IF NOT EXISTS endpoints (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            hostname VARCHAR(255) NOT NULL,
            pool_id UUID REFERENCES pools(id) ON DELETE SET NULL,
            last_seen TIMESTAMP WITH TIME ZONE,
            sync_status VARCHAR(50) DEFAULT 'offline',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(name, hostname)
        )
    """,
    
    "package_states": """
        CREATE TABLE IF NOT EXISTS package_states (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pool_id UUID REFERENCES pools(id) ON DELETE CASCADE,
            endpoint_id UUID REFERENCES endpoints(id) ON DELETE CASCADE,
            state_data JSONB NOT NULL,
            is_target BOOLEAN DEFAULT FALSE,
            pacman_version VARCHAR(50),
            architecture VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """,
    
    "repositories": """
        CREATE TABLE IF NOT EXISTS repositories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            endpoint_id UUID REFERENCES endpoints(id) ON DELETE CASCADE,
            repo_name VARCHAR(255) NOT NULL,
            repo_url VARCHAR(500),
            mirrors JSONB DEFAULT '[]',
            packages JSONB DEFAULT '[]',
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(endpoint_id, repo_name)
        )
    """,
    
    "sync_operations": """
        CREATE TABLE IF NOT EXISTS sync_operations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pool_id UUID REFERENCES pools(id) ON DELETE CASCADE,
            endpoint_id UUID REFERENCES endpoints(id) ON DELETE CASCADE,
            operation_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            details JSONB DEFAULT '{}',
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        )
    """
}

# SQLite schema definitions
SQLITE_SCHEMA = {
    "pools": """
        CREATE TABLE IF NOT EXISTS pools (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            target_state_id TEXT,
            sync_policy TEXT DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "endpoints": """
        CREATE TABLE IF NOT EXISTS endpoints (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            name TEXT NOT NULL,
            hostname TEXT NOT NULL,
            pool_id TEXT REFERENCES pools(id) ON DELETE SET NULL,
            last_seen DATETIME,
            sync_status TEXT DEFAULT 'offline',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, hostname)
        )
    """,
    
    "package_states": """
        CREATE TABLE IF NOT EXISTS package_states (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            pool_id TEXT REFERENCES pools(id) ON DELETE CASCADE,
            endpoint_id TEXT REFERENCES endpoints(id) ON DELETE CASCADE,
            state_data TEXT NOT NULL,
            is_target INTEGER DEFAULT 0,
            pacman_version TEXT,
            architecture TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "repositories": """
        CREATE TABLE IF NOT EXISTS repositories (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            endpoint_id TEXT REFERENCES endpoints(id) ON DELETE CASCADE,
            repo_name TEXT NOT NULL,
            repo_url TEXT,
            mirrors TEXT DEFAULT '[]',
            packages TEXT DEFAULT '[]',
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(endpoint_id, repo_name)
        )
    """,
    
    "sync_operations": """
        CREATE TABLE IF NOT EXISTS sync_operations (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            pool_id TEXT REFERENCES pools(id) ON DELETE CASCADE,
            endpoint_id TEXT REFERENCES endpoints(id) ON DELETE CASCADE,
            operation_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            details TEXT DEFAULT '{}',
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        )
    """
}

# Indexes for better performance
POSTGRESQL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_endpoints_pool_id ON endpoints(pool_id)",
    "CREATE INDEX IF NOT EXISTS idx_endpoints_sync_status ON endpoints(sync_status)",
    "CREATE INDEX IF NOT EXISTS idx_package_states_pool_id ON package_states(pool_id)",
    "CREATE INDEX IF NOT EXISTS idx_package_states_endpoint_id ON package_states(endpoint_id)",
    "CREATE INDEX IF NOT EXISTS idx_package_states_is_target ON package_states(is_target)",
    "CREATE INDEX IF NOT EXISTS idx_repositories_endpoint_id ON repositories(endpoint_id)",
    "CREATE INDEX IF NOT EXISTS idx_sync_operations_pool_id ON sync_operations(pool_id)",
    "CREATE INDEX IF NOT EXISTS idx_sync_operations_endpoint_id ON sync_operations(endpoint_id)",
    "CREATE INDEX IF NOT EXISTS idx_sync_operations_status ON sync_operations(status)",
    "CREATE INDEX IF NOT EXISTS idx_sync_operations_created_at ON sync_operations(created_at)"
]

SQLITE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_endpoints_pool_id ON endpoints(pool_id)",
    "CREATE INDEX IF NOT EXISTS idx_endpoints_sync_status ON endpoints(sync_status)",
    "CREATE INDEX IF NOT EXISTS idx_package_states_pool_id ON package_states(pool_id)",
    "CREATE INDEX IF NOT EXISTS idx_package_states_endpoint_id ON package_states(endpoint_id)",
    "CREATE INDEX IF NOT EXISTS idx_package_states_is_target ON package_states(is_target)",
    "CREATE INDEX IF NOT EXISTS idx_repositories_endpoint_id ON repositories(endpoint_id)",
    "CREATE INDEX IF NOT EXISTS idx_sync_operations_pool_id ON sync_operations(pool_id)",
    "CREATE INDEX IF NOT EXISTS idx_sync_operations_endpoint_id ON sync_operations(endpoint_id)",
    "CREATE INDEX IF NOT EXISTS idx_sync_operations_status ON sync_operations(status)",
    "CREATE INDEX IF NOT EXISTS idx_sync_operations_created_at ON sync_operations(created_at)"
]

# Table creation order (respects foreign key dependencies)
TABLE_ORDER = ["pools", "endpoints", "package_states", "repositories", "sync_operations"]


async def create_tables(db_manager: DatabaseManager) -> bool:
    """Create all database tables and indexes."""
    try:
        schema = POSTGRESQL_SCHEMA if db_manager.database_type == "postgresql" else SQLITE_SCHEMA
        indexes = POSTGRESQL_INDEXES if db_manager.database_type == "postgresql" else SQLITE_INDEXES
        
        logger.info(f"Creating tables for {db_manager.database_type}")
        
        # Create tables in order
        for table_name in TABLE_ORDER:
            if table_name in schema:
                logger.debug(f"Creating table: {table_name}")
                await db_manager.execute(schema[table_name])
        
        # Create indexes
        logger.info("Creating indexes")
        for index_sql in indexes:
            await db_manager.execute(index_sql)
        
        # Add foreign key constraint for pools.target_state_id (after package_states table exists)
        if db_manager.database_type == "postgresql":
            await db_manager.execute("""
                ALTER TABLE pools 
                ADD CONSTRAINT fk_pools_target_state 
                FOREIGN KEY (target_state_id) REFERENCES package_states(id) 
                ON DELETE SET NULL
            """)
        
        logger.info("Database schema created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create database schema: {e}")
        raise


async def drop_tables(db_manager: DatabaseManager) -> bool:
    """Drop all database tables."""
    try:
        logger.warning("Dropping all database tables")
        
        # Drop tables in reverse order to handle foreign key constraints
        for table_name in reversed(TABLE_ORDER):
            try:
                if db_manager.database_type == "postgresql":
                    await db_manager.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                else:  # SQLite
                    await db_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
                logger.debug(f"Dropped table: {table_name}")
            except Exception as e:
                logger.warning(f"Failed to drop table {table_name}: {e}")
        
        logger.info("Database tables dropped successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


async def get_table_info(db_manager: DatabaseManager) -> dict:
    """Get information about existing tables."""
    try:
        if db_manager.database_type == "postgresql":
            query = """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """
        else:  # SQLite
            # For SQLite, we need to query each table individually
            tables_info = {}
            for table_name in TABLE_ORDER:
                try:
                    pragma_result = await db_manager.fetch(f"PRAGMA table_info({table_name})")
                    tables_info[table_name] = pragma_result
                except:
                    # Table doesn't exist
                    pass
            return tables_info
        
        rows = await db_manager.fetch(query)
        
        # Group by table name
        tables_info = {}
        for row in rows:
            table_name = row[0] if isinstance(row, tuple) else row['table_name']
            if table_name not in tables_info:
                tables_info[table_name] = []
            tables_info[table_name].append(row)
        
        return tables_info
        
    except Exception as e:
        logger.error(f"Failed to get table info: {e}")
        return {}


async def verify_schema(db_manager: DatabaseManager) -> bool:
    """Verify that all required tables exist."""
    try:
        table_info = await get_table_info(db_manager)
        
        missing_tables = []
        for table_name in TABLE_ORDER:
            if table_name not in table_info or not table_info[table_name]:
                missing_tables.append(table_name)
        
        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}")
            return False
        
        logger.info("Database schema verification passed")
        return True
        
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        return False