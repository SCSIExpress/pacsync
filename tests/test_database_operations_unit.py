#!/usr/bin/env python3
"""
Unit tests for database operations with both PostgreSQL and SQLite.

Tests database connection management, ORM operations, and schema validation
with mocked database connections to avoid requiring actual database servers.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from server.database.connection import DatabaseManager
from server.database.orm import (
    ORMManager, PoolRepository, EndpointRepository, PackageStateRepository,
    SyncOperationRepository, RepositoryRepository, ValidationError, NotFoundError
)
from server.database.schema import create_tables, verify_schema, get_table_info
from server.database.migrations import MigrationManager
from shared.models import (
    PackagePool, Endpoint, SystemState, PackageState, SyncOperation,
    Repository, RepositoryPackage, SyncStatus, OperationType, OperationStatus,
    SyncPolicy, ConflictResolution
)


class TestDatabaseManager:
    """Test DatabaseManager connection handling."""
    
    @pytest.fixture
    def mock_asyncpg_pool(self):
        """Create mock asyncpg connection pool."""
        pool = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock()
        pool.acquire.return_value.__aexit__ = AsyncMock()
        return pool
    
    @pytest.fixture
    def mock_aiosqlite_connection(self):
        """Create mock aiosqlite connection."""
        conn = AsyncMock()
        conn.execute.return_value = AsyncMock()
        conn.fetchone.return_value = None
        conn.fetchall.return_value = []
        conn.fetchval.return_value = None
        return conn
    
    @pytest.mark.asyncio
    async def test_postgresql_initialization(self, mock_asyncpg_pool):
        """Test PostgreSQL database manager initialization."""
        with patch('server.database.connection.asyncpg.create_pool', return_value=mock_asyncpg_pool):
            db_manager = DatabaseManager("postgresql")
            db_manager.database_url = "postgresql://user:pass@localhost/test"
            
            await db_manager.initialize()
            
            assert db_manager.database_type == "postgresql"
            assert db_manager.pool == mock_asyncpg_pool
            assert db_manager.is_connected() == True
    
    @pytest.mark.asyncio
    async def test_sqlite_initialization(self, mock_aiosqlite_connection):
        """Test SQLite database manager initialization."""
        with patch('server.database.connection.aiosqlite.connect', return_value=mock_aiosqlite_connection):
            db_manager = DatabaseManager("internal")
            
            await db_manager.initialize()
            
            assert db_manager.database_type == "internal"
            assert db_manager.connection == mock_aiosqlite_connection
            assert db_manager.is_connected() == True
    
    @pytest.mark.asyncio
    async def test_postgresql_query_execution(self, mock_asyncpg_pool):
        """Test PostgreSQL query execution."""
        mock_connection = AsyncMock()
        mock_connection.fetchval.return_value = "test-result"
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        with patch('server.database.connection.asyncpg.create_pool', return_value=mock_asyncpg_pool):
            db_manager = DatabaseManager("postgresql")
            db_manager.pool = mock_asyncpg_pool
            
            result = await db_manager.fetchval("SELECT $1", "test-param")
            
            assert result == "test-result"
            mock_connection.fetchval.assert_called_once_with("SELECT $1", "test-param")
    
    @pytest.mark.asyncio
    async def test_sqlite_query_execution(self, mock_aiosqlite_connection):
        """Test SQLite query execution."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone.return_value = ("test-result",)
        mock_aiosqlite_connection.execute.return_value = mock_cursor
        
        with patch('server.database.connection.aiosqlite.connect', return_value=mock_aiosqlite_connection):
            db_manager = DatabaseManager("internal")
            db_manager.connection = mock_aiosqlite_connection
            
            result = await db_manager.fetchval("SELECT ?", "test-param")
            
            assert result == "test-result"
            mock_aiosqlite_connection.execute.assert_called_once_with("SELECT ?", ("test-param",))
    
    def test_get_placeholder_postgresql(self):
        """Test placeholder generation for PostgreSQL."""
        db_manager = DatabaseManager("postgresql")
        
        assert db_manager.get_placeholder() == "$1"
        assert db_manager.get_placeholder(2) == "$2"
        assert db_manager.get_placeholder(10) == "$10"
    
    def test_get_placeholder_sqlite(self):
        """Test placeholder generation for SQLite."""
        db_manager = DatabaseManager("internal")
        
        assert db_manager.get_placeholder() == "?"
        assert db_manager.get_placeholder(2) == "?"
        assert db_manager.get_placeholder(10) == "?"
    
    @pytest.mark.asyncio
    async def test_close_postgresql(self, mock_asyncpg_pool):
        """Test PostgreSQL connection closing."""
        with patch('server.database.connection.asyncpg.create_pool', return_value=mock_asyncpg_pool):
            db_manager = DatabaseManager("postgresql")
            db_manager.pool = mock_asyncpg_pool
            
            await db_manager.close()
            
            mock_asyncpg_pool.close.assert_called_once()
            assert db_manager.pool is None
    
    @pytest.mark.asyncio
    async def test_close_sqlite(self, mock_aiosqlite_connection):
        """Test SQLite connection closing."""
        with patch('server.database.connection.aiosqlite.connect', return_value=mock_aiosqlite_connection):
            db_manager = DatabaseManager("internal")
            db_manager.connection = mock_aiosqlite_connection
            
            await db_manager.close()
            
            mock_aiosqlite_connection.close.assert_called_once()
            assert db_manager.connection is None


class TestPoolRepository:
    """Test PoolRepository ORM operations."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        db_manager = MagicMock()
        db_manager.database_type = "internal"
        db_manager.get_placeholder.side_effect = lambda n=1: "?"
        return db_manager
    
    @pytest.fixture
    def pool_repository(self, mock_db_manager):
        """Create PoolRepository with mocked database."""
        return PoolRepository(mock_db_manager)
    
    @pytest.mark.asyncio
    async def test_create_pool_success(self, pool_repository, mock_db_manager):
        """Test successful pool creation."""
        pool = PackagePool(
            id="pool-1",
            name="Test Pool",
            description="Test description"
        )
        
        mock_db_manager.fetchval.return_value = "pool-1"
        mock_db_manager.execute.return_value = None
        
        result = await pool_repository.create(pool)
        
        assert result.id == "pool-1"
        assert result.name == "Test Pool"
        mock_db_manager.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_pool_duplicate_name(self, pool_repository, mock_db_manager):
        """Test pool creation with duplicate name."""
        pool = PackagePool(
            id="pool-1",
            name="Duplicate Pool",
            description="Test description"
        )
        
        # Mock database constraint violation
        mock_db_manager.execute.side_effect = Exception("UNIQUE constraint failed")
        
        with pytest.raises(ValidationError, match="Pool name already exists"):
            await pool_repository.create(pool)
    
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, pool_repository, mock_db_manager):
        """Test successful pool retrieval by ID."""
        mock_row = {
            'id': 'pool-1',
            'name': 'Test Pool',
            'description': 'Test description',
            'target_state_id': None,
            'sync_policy': '{"auto_sync": false}',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_db_manager.fetchrow.return_value = mock_row
        
        result = await pool_repository.get_by_id("pool-1")
        
        assert result is not None
        assert result.id == "pool-1"
        assert result.name == "Test Pool"
        assert isinstance(result.sync_policy, SyncPolicy)
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, pool_repository, mock_db_manager):
        """Test pool retrieval when pool doesn't exist."""
        mock_db_manager.fetchrow.return_value = None
        
        result = await pool_repository.get_by_id("non-existent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_name_success(self, pool_repository, mock_db_manager):
        """Test successful pool retrieval by name."""
        mock_row = {
            'id': 'pool-1',
            'name': 'Test Pool',
            'description': 'Test description',
            'target_state_id': None,
            'sync_policy': '{"auto_sync": false}',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_db_manager.fetchrow.return_value = mock_row
        
        result = await pool_repository.get_by_name("Test Pool")
        
        assert result is not None
        assert result.name == "Test Pool"
    
    @pytest.mark.asyncio
    async def test_list_all_success(self, pool_repository, mock_db_manager):
        """Test successful pool listing."""
        mock_rows = [
            {
                'id': 'pool-1',
                'name': 'Pool 1',
                'description': 'Description 1',
                'target_state_id': None,
                'sync_policy': '{"auto_sync": false}',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'id': 'pool-2',
                'name': 'Pool 2',
                'description': 'Description 2',
                'target_state_id': None,
                'sync_policy': '{"auto_sync": true}',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
        ]
        mock_db_manager.fetch.return_value = mock_rows
        
        result = await pool_repository.list_all()
        
        assert len(result) == 2
        assert result[0].name == "Pool 1"
        assert result[1].name == "Pool 2"
        assert result[1].sync_policy.auto_sync == True
    
    @pytest.mark.asyncio
    async def test_update_pool_success(self, pool_repository, mock_db_manager):
        """Test successful pool update."""
        # Mock existing pool
        mock_existing = {
            'id': 'pool-1',
            'name': 'Old Name',
            'description': 'Old description',
            'target_state_id': None,
            'sync_policy': '{"auto_sync": false}',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_db_manager.fetchrow.return_value = mock_existing
        mock_db_manager.execute.return_value = None
        
        result = await pool_repository.update("pool-1", name="New Name", description="New description")
        
        assert result.name == "New Name"
        assert result.description == "New description"
        mock_db_manager.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_pool_not_found(self, pool_repository, mock_db_manager):
        """Test pool update when pool doesn't exist."""
        mock_db_manager.fetchrow.return_value = None
        
        with pytest.raises(NotFoundError, match="Pool not found"):
            await pool_repository.update("non-existent", name="New Name")
    
    @pytest.mark.asyncio
    async def test_delete_pool_success(self, pool_repository, mock_db_manager):
        """Test successful pool deletion."""
        mock_db_manager.execute.return_value = None
        mock_db_manager.fetchval.return_value = 1  # 1 row affected
        
        result = await pool_repository.delete("pool-1")
        
        assert result == True
        mock_db_manager.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_delete_pool_not_found(self, pool_repository, mock_db_manager):
        """Test pool deletion when pool doesn't exist."""
        mock_db_manager.fetchval.return_value = 0  # 0 rows affected
        
        result = await pool_repository.delete("non-existent")
        
        assert result == False


class TestEndpointRepository:
    """Test EndpointRepository ORM operations."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        db_manager = MagicMock()
        db_manager.database_type = "internal"
        db_manager.get_placeholder.side_effect = lambda n=1: "?"
        return db_manager
    
    @pytest.fixture
    def endpoint_repository(self, mock_db_manager):
        """Create EndpointRepository with mocked database."""
        return EndpointRepository(mock_db_manager)
    
    @pytest.mark.asyncio
    async def test_create_endpoint_success(self, endpoint_repository, mock_db_manager):
        """Test successful endpoint creation."""
        endpoint = Endpoint(
            id="endpoint-1",
            name="Test Endpoint",
            hostname="test-host"
        )
        
        mock_db_manager.fetchval.return_value = "endpoint-1"
        mock_db_manager.execute.return_value = None
        
        result = await endpoint_repository.create(endpoint)
        
        assert result.id == "endpoint-1"
        assert result.name == "Test Endpoint"
        assert result.hostname == "test-host"
        mock_db_manager.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_endpoint_duplicate_name(self, endpoint_repository, mock_db_manager):
        """Test endpoint creation with duplicate name."""
        endpoint = Endpoint(
            id="endpoint-1",
            name="Duplicate Endpoint",
            hostname="test-host"
        )
        
        mock_db_manager.execute.side_effect = Exception("UNIQUE constraint failed")
        
        with pytest.raises(ValidationError, match="Endpoint name already exists"):
            await endpoint_repository.create(endpoint)
    
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, endpoint_repository, mock_db_manager):
        """Test successful endpoint retrieval by ID."""
        mock_row = {
            'id': 'endpoint-1',
            'name': 'Test Endpoint',
            'hostname': 'test-host',
            'pool_id': 'pool-1',
            'last_seen': datetime.now(),
            'sync_status': 'in_sync',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_db_manager.fetchrow.return_value = mock_row
        
        result = await endpoint_repository.get_by_id("endpoint-1")
        
        assert result is not None
        assert result.id == "endpoint-1"
        assert result.name == "Test Endpoint"
        assert result.hostname == "test-host"
        assert result.pool_id == "pool-1"
        assert result.sync_status == SyncStatus.IN_SYNC
    
    @pytest.mark.asyncio
    async def test_list_by_pool_success(self, endpoint_repository, mock_db_manager):
        """Test successful endpoint listing by pool."""
        mock_rows = [
            {
                'id': 'endpoint-1',
                'name': 'Endpoint 1',
                'hostname': 'host1',
                'pool_id': 'pool-1',
                'last_seen': None,
                'sync_status': 'offline',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'id': 'endpoint-2',
                'name': 'Endpoint 2',
                'hostname': 'host2',
                'pool_id': 'pool-1',
                'last_seen': datetime.now(),
                'sync_status': 'in_sync',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
        ]
        mock_db_manager.fetch.return_value = mock_rows
        
        result = await endpoint_repository.list_by_pool("pool-1")
        
        assert len(result) == 2
        assert result[0].name == "Endpoint 1"
        assert result[0].sync_status == SyncStatus.OFFLINE
        assert result[1].name == "Endpoint 2"
        assert result[1].sync_status == SyncStatus.IN_SYNC
    
    @pytest.mark.asyncio
    async def test_assign_to_pool_success(self, endpoint_repository, mock_db_manager):
        """Test successful endpoint pool assignment."""
        mock_db_manager.execute.return_value = None
        
        result = await endpoint_repository.assign_to_pool("endpoint-1", "pool-1")
        
        assert result == True
        mock_db_manager.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_remove_from_pool_success(self, endpoint_repository, mock_db_manager):
        """Test successful endpoint pool removal."""
        mock_db_manager.execute.return_value = None
        
        result = await endpoint_repository.remove_from_pool("endpoint-1")
        
        assert result == True
        mock_db_manager.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_status_success(self, endpoint_repository, mock_db_manager):
        """Test successful endpoint status update."""
        mock_db_manager.execute.return_value = None
        
        result = await endpoint_repository.update_status("endpoint-1", SyncStatus.IN_SYNC)
        
        assert result == True
        mock_db_manager.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_last_seen_success(self, endpoint_repository, mock_db_manager):
        """Test successful last seen timestamp update."""
        mock_db_manager.execute.return_value = None
        timestamp = datetime.now()
        
        result = await endpoint_repository.update_last_seen("endpoint-1", timestamp)
        
        assert result == True
        mock_db_manager.execute.assert_called()


class TestPackageStateRepository:
    """Test PackageStateRepository ORM operations."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        db_manager = MagicMock()
        db_manager.database_type = "internal"
        db_manager.get_placeholder.side_effect = lambda n=1: "?"
        return db_manager
    
    @pytest.fixture
    def state_repository(self, mock_db_manager):
        """Create PackageStateRepository with mocked database."""
        return PackageStateRepository(mock_db_manager)
    
    @pytest.mark.asyncio
    async def test_save_state_success(self, state_repository, mock_db_manager):
        """Test successful state saving."""
        packages = [
            PackageState("pkg1", "1.0.0", "core", 1024, ["dep1"]),
            PackageState("pkg2", "2.0.0", "extra", 2048, [])
        ]
        system_state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=packages,
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        mock_db_manager.fetchval.return_value = "state-1"
        mock_db_manager.execute.return_value = None
        
        result = await state_repository.save_state("pool-1", "endpoint-1", system_state)
        
        assert result == "state-1"
        mock_db_manager.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_state_success(self, state_repository, mock_db_manager):
        """Test successful state retrieval."""
        mock_row = {
            'id': 'state-1',
            'pool_id': 'pool-1',
            'endpoint_id': 'endpoint-1',
            'state_data': '{"packages": [{"package_name": "pkg1", "version": "1.0.0", "repository": "core", "installed_size": 1024, "dependencies": []}], "pacman_version": "6.0.1", "architecture": "x86_64"}',
            'is_target': False,
            'created_at': datetime.now()
        }
        mock_db_manager.fetchrow.return_value = mock_row
        
        result = await state_repository.get_state("state-1")
        
        assert result is not None
        assert result.endpoint_id == "endpoint-1"
        assert len(result.packages) == 1
        assert result.packages[0].package_name == "pkg1"
        assert result.pacman_version == "6.0.1"
        assert result.architecture == "x86_64"
    
    @pytest.mark.asyncio
    async def test_get_state_not_found(self, state_repository, mock_db_manager):
        """Test state retrieval when state doesn't exist."""
        mock_db_manager.fetchrow.return_value = None
        
        result = await state_repository.get_state("non-existent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_target_state_success(self, state_repository, mock_db_manager):
        """Test successful target state setting."""
        mock_db_manager.execute.return_value = None
        
        result = await state_repository.set_target_state("pool-1", "state-1")
        
        assert result == True
        # Should call execute twice: clear old target, set new target
        assert mock_db_manager.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_latest_target_state_success(self, state_repository, mock_db_manager):
        """Test successful latest target state retrieval."""
        mock_row = {
            'id': 'state-1',
            'pool_id': 'pool-1',
            'endpoint_id': 'endpoint-1',
            'state_data': '{"packages": [], "pacman_version": "6.0.1", "architecture": "x86_64"}',
            'is_target': True,
            'created_at': datetime.now()
        }
        mock_db_manager.fetchrow.return_value = mock_row
        
        result = await state_repository.get_latest_target_state("pool-1")
        
        assert result is not None
        assert result.endpoint_id == "endpoint-1"
    
    @pytest.mark.asyncio
    async def test_get_endpoint_states_success(self, state_repository, mock_db_manager):
        """Test successful endpoint states retrieval."""
        mock_rows = [
            {
                'id': 'state-1',
                'pool_id': 'pool-1',
                'endpoint_id': 'endpoint-1',
                'state_data': '{"packages": [], "pacman_version": "6.0.1", "architecture": "x86_64"}',
                'is_target': False,
                'created_at': datetime.now()
            },
            {
                'id': 'state-2',
                'pool_id': 'pool-1',
                'endpoint_id': 'endpoint-1',
                'state_data': '{"packages": [], "pacman_version": "6.0.1", "architecture": "x86_64"}',
                'is_target': False,
                'created_at': datetime.now()
            }
        ]
        mock_db_manager.fetch.return_value = mock_rows
        
        result = await state_repository.get_endpoint_states("endpoint-1", limit=5)
        
        assert len(result) == 2
        assert all(state.endpoint_id == "endpoint-1" for state in result)


class TestSchemaOperations:
    """Test database schema operations."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        db_manager = MagicMock()
        db_manager.database_type = "internal"
        db_manager.execute.return_value = None
        return db_manager
    
    @pytest.mark.asyncio
    async def test_create_tables_success(self, mock_db_manager):
        """Test successful table creation."""
        await create_tables(mock_db_manager)
        
        # Should execute multiple CREATE TABLE statements
        assert mock_db_manager.execute.call_count >= 5
    
    @pytest.mark.asyncio
    async def test_verify_schema_success(self, mock_db_manager):
        """Test successful schema verification."""
        # Mock table existence checks
        mock_db_manager.fetchval.return_value = 1  # Table exists
        
        result = await verify_schema(mock_db_manager)
        
        assert result == True
        # Should check for all required tables
        assert mock_db_manager.fetchval.call_count >= 5
    
    @pytest.mark.asyncio
    async def test_verify_schema_missing_table(self, mock_db_manager):
        """Test schema verification with missing table."""
        # Mock some tables missing
        mock_db_manager.fetchval.side_effect = [1, 1, 0, 1, 1]  # Third table missing
        
        result = await verify_schema(mock_db_manager)
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_get_table_info_success(self, mock_db_manager):
        """Test successful table info retrieval."""
        mock_tables = [
            {'table_name': 'pools'},
            {'table_name': 'endpoints'},
            {'table_name': 'package_states'},
            {'table_name': 'repositories'},
            {'table_name': 'sync_operations'}
        ]
        mock_db_manager.fetch.return_value = mock_tables
        
        result = await get_table_info(mock_db_manager)
        
        assert len(result) == 5
        assert 'pools' in result
        assert 'endpoints' in result
        assert 'package_states' in result


class TestMigrationManager:
    """Test database migration management."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        db_manager = MagicMock()
        db_manager.database_type = "internal"
        db_manager.execute.return_value = None
        db_manager.fetchval.return_value = 0  # No migrations applied
        return db_manager
    
    @pytest.fixture
    def migration_manager(self, mock_db_manager):
        """Create MigrationManager with mocked database."""
        return MigrationManager(mock_db_manager)
    
    @pytest.mark.asyncio
    async def test_get_migration_status_no_migrations(self, migration_manager, mock_db_manager):
        """Test migration status when no migrations are applied."""
        mock_db_manager.fetchval.return_value = 0
        
        status = await migration_manager.get_migration_status()
        
        assert status['applied_migrations'] == 0
        assert status['pending_migrations'] >= 0
    
    @pytest.mark.asyncio
    async def test_get_migration_status_with_migrations(self, migration_manager, mock_db_manager):
        """Test migration status with applied migrations."""
        mock_db_manager.fetchval.return_value = 3
        
        status = await migration_manager.get_migration_status()
        
        assert status['applied_migrations'] == 3
    
    @pytest.mark.asyncio
    async def test_apply_migration_success(self, migration_manager, mock_db_manager):
        """Test successful migration application."""
        mock_db_manager.execute.return_value = None
        
        result = await migration_manager.apply_migration("001_initial_schema.sql", "CREATE TABLE test;")
        
        assert result == True
        # Should execute the migration and record it
        assert mock_db_manager.execute.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_rollback_migration_success(self, migration_manager, mock_db_manager):
        """Test successful migration rollback."""
        mock_db_manager.execute.return_value = None
        
        result = await migration_manager.rollback_migration("001_initial_schema.sql", "DROP TABLE test;")
        
        assert result == True
        # Should execute rollback and remove migration record
        assert mock_db_manager.execute.call_count >= 2


class TestORMManager:
    """Test ORMManager integration."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        return MagicMock()
    
    @pytest.fixture
    def orm_manager(self, mock_db_manager):
        """Create ORMManager with mocked database."""
        return ORMManager(mock_db_manager)
    
    def test_orm_manager_initialization(self, orm_manager):
        """Test ORMManager initialization."""
        assert orm_manager.db_manager is not None
        assert isinstance(orm_manager.pools, PoolRepository)
        assert isinstance(orm_manager.endpoints, EndpointRepository)
        assert isinstance(orm_manager.package_states, PackageStateRepository)
        assert isinstance(orm_manager.sync_operations, SyncOperationRepository)
        assert isinstance(orm_manager.repositories, RepositoryRepository)
    
    def test_repository_access(self, orm_manager):
        """Test repository access through ORM manager."""
        # All repositories should be accessible
        repositories = [
            orm_manager.pools,
            orm_manager.endpoints,
            orm_manager.package_states,
            orm_manager.sync_operations,
            orm_manager.repositories
        ]
        
        for repo in repositories:
            assert repo is not None
            assert hasattr(repo, 'db_manager')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])