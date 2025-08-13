"""
Database migration system for the Pacman Sync Utility.

This module provides database migration utilities to handle schema changes
and data migrations for both PostgreSQL and SQLite backends.
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from .connection import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Represents a database migration."""
    version: str
    description: str
    up_sql: str
    down_sql: str
    requires_data_migration: bool = False
    data_migration_func: Optional[Callable] = None


class MigrationManager:
    """Manages database migrations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.migrations: List[Migration] = []
        self._init_migrations()
    
    def _init_migrations(self):
        """Initialize the list of available migrations."""
        # Migration 001: Initial schema
        self.migrations.append(Migration(
            version="001",
            description="Initial database schema",
            up_sql=self._get_initial_schema_sql(),
            down_sql=self._get_drop_all_tables_sql()
        ))
        
        # Migration 002: Add updated_at triggers (PostgreSQL only)
        if self.db_manager.database_type == "postgresql":
            self.migrations.append(Migration(
                version="002",
                description="Add updated_at triggers",
                up_sql=self._get_updated_at_triggers_sql(),
                down_sql=self._get_drop_triggers_sql()
            ))
        
        # Migration 003: Add indexes for performance
        self.migrations.append(Migration(
            version="003",
            description="Add performance indexes",
            up_sql=self._get_indexes_sql(),
            down_sql=self._get_drop_indexes_sql()
        ))
        
        # Migration 004: Add mirrors column to repositories table
        self.migrations.append(Migration(
            version="004",
            description="Add mirrors column to repositories table",
            up_sql=self._get_add_mirrors_column_sql(),
            down_sql=self._get_drop_mirrors_column_sql()
        ))
    
    def _get_initial_schema_sql(self) -> str:
        """Get SQL for initial schema creation."""
        if self.db_manager.database_type == "postgresql":
            return """
                -- Enable UUID extension
                CREATE EXTENSION IF NOT EXISTS "pgcrypto";
                
                -- Create pools table
                CREATE TABLE IF NOT EXISTS pools (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL UNIQUE,
                    description TEXT,
                    target_state_id UUID,
                    sync_policy JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                
                -- Create endpoints table
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
                );
                
                -- Create package_states table
                CREATE TABLE IF NOT EXISTS package_states (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    pool_id UUID REFERENCES pools(id) ON DELETE CASCADE,
                    endpoint_id UUID REFERENCES endpoints(id) ON DELETE CASCADE,
                    state_data JSONB NOT NULL,
                    is_target BOOLEAN DEFAULT FALSE,
                    pacman_version VARCHAR(50),
                    architecture VARCHAR(50),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                
                -- Create repositories table
                CREATE TABLE IF NOT EXISTS repositories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    endpoint_id UUID REFERENCES endpoints(id) ON DELETE CASCADE,
                    repo_name VARCHAR(255) NOT NULL,
                    repo_url VARCHAR(500),
                    packages JSONB DEFAULT '[]',
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(endpoint_id, repo_name)
                );
                
                -- Create sync_operations table
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
                );
                
                -- Add foreign key constraint for pools.target_state_id
                ALTER TABLE pools 
                ADD CONSTRAINT fk_pools_target_state 
                FOREIGN KEY (target_state_id) REFERENCES package_states(id) 
                ON DELETE SET NULL;
            """
        else:  # SQLite
            return """
                -- Create pools table
                CREATE TABLE IF NOT EXISTS pools (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    target_state_id TEXT,
                    sync_policy TEXT DEFAULT '{}',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create endpoints table
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
                );
                
                -- Create package_states table
                CREATE TABLE IF NOT EXISTS package_states (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    pool_id TEXT REFERENCES pools(id) ON DELETE CASCADE,
                    endpoint_id TEXT REFERENCES endpoints(id) ON DELETE CASCADE,
                    state_data TEXT NOT NULL,
                    is_target INTEGER DEFAULT 0,
                    pacman_version TEXT,
                    architecture TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create repositories table
                CREATE TABLE IF NOT EXISTS repositories (
                    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                    endpoint_id TEXT REFERENCES endpoints(id) ON DELETE CASCADE,
                    repo_name TEXT NOT NULL,
                    repo_url TEXT,
                    packages TEXT DEFAULT '[]',
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(endpoint_id, repo_name)
                );
                
                -- Create sync_operations table
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
                );
            """
    
    def _get_drop_all_tables_sql(self) -> str:
        """Get SQL to drop all tables."""
        return """
            DROP TABLE IF EXISTS sync_operations CASCADE;
            DROP TABLE IF EXISTS repositories CASCADE;
            DROP TABLE IF EXISTS package_states CASCADE;
            DROP TABLE IF EXISTS endpoints CASCADE;
            DROP TABLE IF EXISTS pools CASCADE;
        """
    
    def _get_updated_at_triggers_sql(self) -> str:
        """Get SQL for updated_at triggers (PostgreSQL only)."""
        return """
            -- Function to update updated_at timestamp
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
            
            -- Triggers for pools table
            CREATE TRIGGER update_pools_updated_at 
                BEFORE UPDATE ON pools 
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            
            -- Triggers for endpoints table
            CREATE TRIGGER update_endpoints_updated_at 
                BEFORE UPDATE ON endpoints 
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    
    def _get_drop_triggers_sql(self) -> str:
        """Get SQL to drop triggers (PostgreSQL only)."""
        return """
            DROP TRIGGER IF EXISTS update_pools_updated_at ON pools;
            DROP TRIGGER IF EXISTS update_endpoints_updated_at ON endpoints;
            DROP FUNCTION IF EXISTS update_updated_at_column();
        """
    
    def _get_indexes_sql(self) -> str:
        """Get SQL for performance indexes."""
        return """
            CREATE INDEX IF NOT EXISTS idx_endpoints_pool_id ON endpoints(pool_id);
            CREATE INDEX IF NOT EXISTS idx_endpoints_sync_status ON endpoints(sync_status);
            CREATE INDEX IF NOT EXISTS idx_package_states_pool_id ON package_states(pool_id);
            CREATE INDEX IF NOT EXISTS idx_package_states_endpoint_id ON package_states(endpoint_id);
            CREATE INDEX IF NOT EXISTS idx_package_states_is_target ON package_states(is_target);
            CREATE INDEX IF NOT EXISTS idx_repositories_endpoint_id ON repositories(endpoint_id);
            CREATE INDEX IF NOT EXISTS idx_sync_operations_pool_id ON sync_operations(pool_id);
            CREATE INDEX IF NOT EXISTS idx_sync_operations_endpoint_id ON sync_operations(endpoint_id);
            CREATE INDEX IF NOT EXISTS idx_sync_operations_status ON sync_operations(status);
            CREATE INDEX IF NOT EXISTS idx_sync_operations_created_at ON sync_operations(created_at);
        """
    
    def _get_drop_indexes_sql(self) -> str:
        """Get SQL to drop indexes."""
        return """
            DROP INDEX IF EXISTS idx_endpoints_pool_id;
            DROP INDEX IF EXISTS idx_endpoints_sync_status;
            DROP INDEX IF EXISTS idx_package_states_pool_id;
            DROP INDEX IF EXISTS idx_package_states_endpoint_id;
            DROP INDEX IF EXISTS idx_package_states_is_target;
            DROP INDEX IF EXISTS idx_repositories_endpoint_id;
            DROP INDEX IF EXISTS idx_sync_operations_pool_id;
            DROP INDEX IF EXISTS idx_sync_operations_endpoint_id;
            DROP INDEX IF EXISTS idx_sync_operations_status;
            DROP INDEX IF EXISTS idx_sync_operations_created_at;
        """
    
    def _get_add_mirrors_column_sql(self) -> str:
        """Get SQL to add mirrors column to repositories table."""
        if self.db_manager.database_type == "postgresql":
            return """
                ALTER TABLE repositories 
                ADD COLUMN IF NOT EXISTS mirrors JSONB DEFAULT '[]';
                
                -- Create index for mirror queries
                CREATE INDEX IF NOT EXISTS idx_repositories_mirrors 
                ON repositories USING GIN (mirrors);
            """
        else:  # SQLite
            return """
                ALTER TABLE repositories 
                ADD COLUMN mirrors TEXT DEFAULT '[]';
            """
    
    def _get_drop_mirrors_column_sql(self) -> str:
        """Get SQL to drop mirrors column from repositories table."""
        if self.db_manager.database_type == "postgresql":
            return """
                DROP INDEX IF EXISTS idx_repositories_mirrors;
                ALTER TABLE repositories DROP COLUMN IF EXISTS mirrors;
            """
        else:  # SQLite
            # SQLite doesn't support DROP COLUMN, so we'd need to recreate the table
            # For now, just leave the column (it won't hurt anything)
            return "-- SQLite doesn't support DROP COLUMN, column will remain"
    
    async def _create_migrations_table(self):
        """Create the migrations tracking table."""
        if self.db_manager.database_type == "postgresql":
            sql = """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(50) PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
        else:  # SQLite
            sql = """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
        
        await self.db_manager.execute(sql)
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        try:
            await self._create_migrations_table()
            rows = await self.db_manager.fetch("SELECT version FROM schema_migrations ORDER BY version")
            return [row[0] if isinstance(row, tuple) else row['version'] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get applied migrations: {e}")
            return []
    
    async def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations."""
        applied = await self.get_applied_migrations()
        return [m for m in self.migrations if m.version not in applied]
    
    async def apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration."""
        try:
            logger.info(f"Applying migration {migration.version}: {migration.description}")
            
            # Execute the migration SQL
            for statement in migration.up_sql.split(';'):
                statement = statement.strip()
                if statement:
                    await self.db_manager.execute(statement)
            
            # Run data migration if required
            if migration.requires_data_migration and migration.data_migration_func:
                logger.info(f"Running data migration for {migration.version}")
                await migration.data_migration_func(self.db_manager)
            
            # Record the migration as applied
            await self.db_manager.execute(
                f"INSERT INTO schema_migrations (version, description) VALUES ({self.db_manager.get_placeholder()}, {self.db_manager.get_placeholder(2)})",
                migration.version, migration.description
            )
            
            logger.info(f"Migration {migration.version} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply migration {migration.version}: {e}")
            raise
    
    async def rollback_migration(self, migration: Migration) -> bool:
        """Rollback a single migration."""
        try:
            logger.warning(f"Rolling back migration {migration.version}: {migration.description}")
            
            # Execute the rollback SQL
            for statement in migration.down_sql.split(';'):
                statement = statement.strip()
                if statement:
                    await self.db_manager.execute(statement)
            
            # Remove the migration record
            await self.db_manager.execute(
                f"DELETE FROM schema_migrations WHERE version = {self.db_manager.get_placeholder()}",
                migration.version
            )
            
            logger.info(f"Migration {migration.version} rolled back successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback migration {migration.version}: {e}")
            raise
    
    async def migrate_up(self, target_version: Optional[str] = None) -> bool:
        """Apply all pending migrations up to target version."""
        try:
            pending = await self.get_pending_migrations()
            
            if target_version:
                # Filter to only migrations up to target version
                pending = [m for m in pending if m.version <= target_version]
            
            if not pending:
                logger.info("No pending migrations to apply")
                return True
            
            logger.info(f"Applying {len(pending)} migrations")
            
            for migration in pending:
                await self.apply_migration(migration)
            
            logger.info("All migrations applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
    
    async def migrate_down(self, target_version: str) -> bool:
        """Rollback migrations down to target version."""
        try:
            applied = await self.get_applied_migrations()
            
            # Find migrations to rollback (in reverse order)
            to_rollback = []
            for migration in reversed(self.migrations):
                if migration.version in applied and migration.version > target_version:
                    to_rollback.append(migration)
            
            if not to_rollback:
                logger.info(f"No migrations to rollback to version {target_version}")
                return True
            
            logger.warning(f"Rolling back {len(to_rollback)} migrations")
            
            for migration in to_rollback:
                await self.rollback_migration(migration)
            
            logger.info(f"Rollback to version {target_version} completed")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status."""
        try:
            applied = await self.get_applied_migrations()
            pending = await self.get_pending_migrations()
            
            return {
                "database_type": self.db_manager.database_type,
                "total_migrations": len(self.migrations),
                "applied_count": len(applied),
                "pending_count": len(pending),
                "applied_versions": applied,
                "pending_versions": [m.version for m in pending],
                "current_version": applied[-1] if applied else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {"error": str(e)}


async def run_migrations(db_manager: DatabaseManager, target_version: Optional[str] = None) -> bool:
    """Run database migrations."""
    migration_manager = MigrationManager(db_manager)
    return await migration_manager.migrate_up(target_version)


async def rollback_migrations(db_manager: DatabaseManager, target_version: str) -> bool:
    """Rollback database migrations."""
    migration_manager = MigrationManager(db_manager)
    return await migration_manager.migrate_down(target_version)


async def get_migration_status(db_manager: DatabaseManager) -> Dict[str, Any]:
    """Get migration status."""
    migration_manager = MigrationManager(db_manager)
    return await migration_manager.get_migration_status()