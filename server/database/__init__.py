"""
Database package for the Pacman Sync Utility Server.

This package provides database connection management, schema definitions,
and migration utilities for both PostgreSQL and SQLite backends.
"""

from .connection import DatabaseManager, get_database_manager
from .schema import create_tables, drop_tables
from .migrations import MigrationManager, run_migrations, get_migration_status

__all__ = [
    'DatabaseManager',
    'get_database_manager', 
    'create_tables',
    'drop_tables',
    'MigrationManager',
    'run_migrations',
    'get_migration_status'
]