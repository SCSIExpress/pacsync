"""
Database connection management for the Pacman Sync Utility.

This module provides database connection management with support for both
PostgreSQL and SQLite backends, configured via environment variables.
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import sqlite3
from pathlib import Path

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections for both PostgreSQL and SQLite."""
    
    def __init__(self, database_type: str = "internal", database_url: Optional[str] = None):
        self.database_type = database_type.lower()
        self.database_url = database_url
        self._pool = None
        self._connection = None
        
        if self.database_type == "postgresql" and not ASYNCPG_AVAILABLE:
            raise ImportError("asyncpg is required for PostgreSQL support. Install with: pip install asyncpg")
        
        if self.database_type == "internal" and not AIOSQLITE_AVAILABLE:
            raise ImportError("aiosqlite is required for SQLite support. Install with: pip install aiosqlite")
    
    async def initialize(self):
        """Initialize the database connection."""
        if self.database_type == "postgresql":
            await self._init_postgresql()
        elif self.database_type == "internal":
            await self._init_sqlite()
        else:
            raise ValueError(f"Unsupported database type: {self.database_type}")
        
        logger.info(f"Database initialized: {self.database_type}")
    
    async def _init_postgresql(self):
        """Initialize PostgreSQL connection pool with enhanced configuration."""
        if not self.database_url:
            raise ValueError("DATABASE_URL is required for PostgreSQL")
        
        try:
            from server.config import get_config
            config = get_config()
            
            # Enhanced pool configuration for horizontal scaling
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=config.database.pool_min_size,
                max_size=config.database.pool_max_size,
                command_timeout=60,
                server_settings={
                    'application_name': 'pacman-sync-utility',
                    'tcp_keepalives_idle': '600',
                    'tcp_keepalives_interval': '30',
                    'tcp_keepalives_count': '3',
                },
                # Connection lifecycle callbacks
                init=self._init_connection,
                setup=self._setup_connection,
                # Pool management settings
                max_queries=50000,  # Recycle connections after 50k queries
                max_inactive_connection_lifetime=300,  # 5 minutes
            )
            logger.info(f"PostgreSQL connection pool created (min={config.database.pool_min_size}, max={config.database.pool_max_size})")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL pool: {e}")
            raise
    
    async def _init_sqlite(self):
        """Initialize SQLite connection."""
        # Create data directory if it doesn't exist
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        db_path = data_dir / "pacman_sync.db"
        self.database_url = str(db_path)
        
        try:
            # Test connection
            self._connection = await aiosqlite.connect(self.database_url)
            await self._connection.execute("PRAGMA foreign_keys = ON")
            await self._connection.commit()
            logger.info(f"SQLite database initialized: {self.database_url}")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {e}")
            raise
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection context manager."""
        if self.database_type == "postgresql":
            async with self._pool.acquire() as conn:
                yield conn
        elif self.database_type == "internal":
            if self._connection is None:
                self._connection = await aiosqlite.connect(self.database_url)
                await self._connection.execute("PRAGMA foreign_keys = ON")
            yield self._connection
        else:
            raise ValueError(f"Unsupported database type: {self.database_type}")
    
    async def execute(self, query: str, *args) -> Any:
        """Execute a query and return the result."""
        async with self.get_connection() as conn:
            if self.database_type == "postgresql":
                return await conn.execute(query, *args)
            else:  # SQLite
                cursor = await conn.execute(query, args)
                await conn.commit()
                return cursor
    
    async def fetch(self, query: str, *args) -> list:
        """Fetch multiple rows from a query."""
        async with self.get_connection() as conn:
            if self.database_type == "postgresql":
                return await conn.fetch(query, *args)
            else:  # SQLite
                cursor = await conn.execute(query, args)
                return await cursor.fetchall()
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch a single row from a query."""
        async with self.get_connection() as conn:
            if self.database_type == "postgresql":
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
            else:  # SQLite
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(query, args)
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single value from a query."""
        async with self.get_connection() as conn:
            if self.database_type == "postgresql":
                return await conn.fetchval(query, *args)
            else:  # SQLite
                cursor = await conn.execute(query, args)
                row = await cursor.fetchone()
                return row[0] if row else None
    
    async def _init_connection(self, conn):
        """Initialize a new PostgreSQL connection."""
        # Set connection-level settings for better performance
        await conn.execute("SET timezone = 'UTC'")
        await conn.execute("SET statement_timeout = '30s'")
        await conn.execute("SET lock_timeout = '10s'")
    
    async def _setup_connection(self, conn):
        """Set up a PostgreSQL connection after it's acquired from the pool."""
        # This is called every time a connection is acquired
        # Can be used for connection-specific setup
        pass
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics for monitoring."""
        if self.database_type == "postgresql" and self._pool:
            return {
                "type": "postgresql",
                "size": self._pool.get_size(),
                "min_size": self._pool.get_min_size(),
                "max_size": self._pool.get_max_size(),
                "idle_connections": self._pool.get_idle_size(),
                "active_connections": self._pool.get_size() - self._pool.get_idle_size(),
            }
        elif self.database_type == "internal":
            return {
                "type": "sqlite",
                "connection_status": "connected" if self._connection else "disconnected"
            }
        else:
            return {"type": "unknown"}
    
    async def health_check(self) -> bool:
        """Perform a health check on the database connection."""
        try:
            if self.database_type == "postgresql" and self._pool:
                async with self._pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                return True
            elif self.database_type == "internal" and self._connection:
                await self._connection.execute("SELECT 1")
                return True
            return False
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def close(self):
        """Close database connections gracefully."""
        if self.database_type == "postgresql" and self._pool:
            # Wait for active connections to finish with timeout
            try:
                await asyncio.wait_for(self._pool.close(), timeout=10.0)
                logger.info("PostgreSQL connection pool closed gracefully")
            except asyncio.TimeoutError:
                logger.warning("PostgreSQL pool close timed out, forcing termination")
                self._pool.terminate()
        elif self.database_type == "internal" and self._connection:
            await self._connection.close()
            logger.info("SQLite connection closed")
    
    def get_placeholder(self, index: int = 1) -> str:
        """Get the appropriate parameter placeholder for the database type."""
        if self.database_type == "postgresql":
            return f"${index}"
        else:  # SQLite
            return "?"
    
    def get_returning_clause(self) -> str:
        """Get the appropriate RETURNING clause for the database type."""
        if self.database_type == "postgresql":
            return "RETURNING *"
        else:  # SQLite doesn't support RETURNING in all contexts
            return ""


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        from server.config import get_config
        config = get_config()
        _db_manager = DatabaseManager(config.database.type, config.database.url)
    return _db_manager


async def initialize_database():
    """Initialize the global database manager."""
    db_manager = get_database_manager()
    await db_manager.initialize()
    return db_manager


async def close_database():
    """Close the global database manager."""
    global _db_manager
    if _db_manager:
        await _db_manager.close()
        _db_manager = None