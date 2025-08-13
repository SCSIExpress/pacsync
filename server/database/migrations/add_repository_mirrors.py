"""
Migration to add mirrors column to repositories table.

This migration adds support for storing multiple mirror URLs per repository,
which is needed for the pacman-conf integration that provides complete
mirror information from the client.
"""

from server.database.migrations.base import Migration


class AddRepositoryMirrorsMigration(Migration):
    """Add mirrors column to repositories table."""
    
    version = "20241208_001"
    description = "Add mirrors column to repositories table"
    
    def up_postgresql(self, connection):
        """Apply migration for PostgreSQL."""
        connection.execute("""
            ALTER TABLE repositories 
            ADD COLUMN IF NOT EXISTS mirrors JSONB DEFAULT '[]'
        """)
        
        # Create index for mirror queries
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_repositories_mirrors 
            ON repositories USING GIN (mirrors)
        """)
    
    def up_sqlite(self, connection):
        """Apply migration for SQLite."""
        # SQLite doesn't support ADD COLUMN IF NOT EXISTS, so check first
        cursor = connection.execute("""
            PRAGMA table_info(repositories)
        """)
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'mirrors' not in columns:
            connection.execute("""
                ALTER TABLE repositories 
                ADD COLUMN mirrors TEXT DEFAULT '[]'
            """)
    
    def down_postgresql(self, connection):
        """Rollback migration for PostgreSQL."""
        connection.execute("""
            DROP INDEX IF EXISTS idx_repositories_mirrors
        """)
        connection.execute("""
            ALTER TABLE repositories 
            DROP COLUMN IF EXISTS mirrors
        """)
    
    def down_sqlite(self, connection):
        """Rollback migration for SQLite."""
        # SQLite doesn't support DROP COLUMN, so we'd need to recreate the table
        # For now, just leave the column (it won't hurt anything)
        pass


# Register the migration
migration = AddRepositoryMirrorsMigration()