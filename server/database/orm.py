"""
ORM layer for the Pacman Sync Utility.

This module provides database operations (CRUD) for all core entities
with validation logic for data integrity and business rules.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from shared.models import (
    PackagePool, Endpoint, SystemState, PackageState, SyncOperation,
    Repository, RepositoryPackage, SyncStatus, OperationType, OperationStatus,
    SyncPolicy, ConflictResolution
)
from .connection import DatabaseManager

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


class NotFoundError(Exception):
    """Raised when a requested entity is not found."""
    pass


class PoolRepository:
    """Repository for PackagePool operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create(self, pool: PackagePool) -> PackagePool:
        """Create a new package pool."""
        # Validate pool data
        if not pool.name.strip():
            raise ValidationError("Pool name cannot be empty")
        
        # Check for duplicate names
        existing = await self.get_by_name(pool.name)
        if existing:
            raise ValidationError(f"Pool with name '{pool.name}' already exists")
        
        # Prepare data for insertion
        sync_policy_json = json.dumps(pool.sync_policy.to_dict())
        
        if self.db.database_type == "postgresql":
            query = """
                INSERT INTO pools (id, name, description, sync_policy, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
            """
            row = await self.db.fetchrow(
                query, pool.id, pool.name, pool.description,
                sync_policy_json, pool.created_at, pool.updated_at
            )
        else:  # SQLite
            query = """
                INSERT INTO pools (id, name, description, sync_policy, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            await self.db.execute(
                query, pool.id, pool.name, pool.description,
                sync_policy_json, pool.created_at.isoformat(), pool.updated_at.isoformat()
            )
            row = await self.db.fetchrow("SELECT * FROM pools WHERE id = ?", pool.id)
        
        return self._row_to_pool(row)
    
    async def get_by_id(self, pool_id: str) -> Optional[PackagePool]:
        """Get a pool by ID."""
        if self.db.database_type == "postgresql":
            query = "SELECT * FROM pools WHERE id = $1"
        else:
            query = "SELECT * FROM pools WHERE id = ?"
        
        row = await self.db.fetchrow(query, pool_id)
        return self._row_to_pool(row) if row else None
    
    async def get_by_name(self, name: str) -> Optional[PackagePool]:
        """Get a pool by name."""
        if self.db.database_type == "postgresql":
            query = "SELECT * FROM pools WHERE name = $1"
        else:
            query = "SELECT * FROM pools WHERE name = ?"
        
        row = await self.db.fetchrow(query, name)
        return self._row_to_pool(row) if row else None
    
    async def list_all(self) -> List[PackagePool]:
        """List all pools."""
        query = "SELECT * FROM pools ORDER BY created_at"
        rows = await self.db.fetch(query)
        return [self._row_to_pool(row) for row in rows]
    
    async def update(self, pool_id: str, **kwargs) -> PackagePool:
        """Update a pool."""
        pool = await self.get_by_id(pool_id)
        if not pool:
            raise NotFoundError(f"Pool with ID {pool_id} not found")
        
        # Update fields
        if 'name' in kwargs:
            if not kwargs['name'].strip():
                raise ValidationError("Pool name cannot be empty")
            # Check for duplicate names (excluding current pool)
            existing = await self.get_by_name(kwargs['name'])
            if existing and existing.id != pool_id:
                raise ValidationError(f"Pool with name '{kwargs['name']}' already exists")
            pool.name = kwargs['name']
        
        if 'description' in kwargs:
            pool.description = kwargs['description']
        
        if 'sync_policy' in kwargs:
            if isinstance(kwargs['sync_policy'], dict):
                pool.sync_policy = SyncPolicy(
                    auto_sync=kwargs['sync_policy'].get('auto_sync', False),
                    exclude_packages=kwargs['sync_policy'].get('exclude_packages', []),
                    include_aur=kwargs['sync_policy'].get('include_aur', False),
                    conflict_resolution=ConflictResolution(
                        kwargs['sync_policy'].get('conflict_resolution', 'manual')
                    )
                )
            else:
                pool.sync_policy = kwargs['sync_policy']
        
        if 'target_state_id' in kwargs:
            pool.target_state_id = kwargs['target_state_id']
        
        pool.updated_at = datetime.now()
        
        # Save to database
        sync_policy_json = json.dumps(pool.sync_policy.to_dict())
        
        if self.db.database_type == "postgresql":
            query = """
                UPDATE pools 
                SET name = $2, description = $3, target_state_id = $4, 
                    sync_policy = $5, updated_at = $6
                WHERE id = $1
                RETURNING *
            """
            row = await self.db.fetchrow(
                query, pool_id, pool.name, pool.description,
                pool.target_state_id, sync_policy_json, pool.updated_at
            )
        else:  # SQLite
            query = """
                UPDATE pools 
                SET name = ?, description = ?, target_state_id = ?, 
                    sync_policy = ?, updated_at = ?
                WHERE id = ?
            """
            await self.db.execute(
                query, pool.name, pool.description, pool.target_state_id,
                sync_policy_json, pool.updated_at.isoformat(), pool_id
            )
            row = await self.db.fetchrow("SELECT * FROM pools WHERE id = ?", pool_id)
        
        return self._row_to_pool(row)
    
    async def delete(self, pool_id: str) -> bool:
        """Delete a pool."""
        pool = await self.get_by_id(pool_id)
        if not pool:
            return False
        
        if self.db.database_type == "postgresql":
            query = "DELETE FROM pools WHERE id = $1"
        else:
            query = "DELETE FROM pools WHERE id = ?"
        
        await self.db.execute(query, pool_id)
        return True
    
    async def get_endpoints(self, pool_id: str) -> List[str]:
        """Get endpoint IDs for a pool."""
        if self.db.database_type == "postgresql":
            query = "SELECT id FROM endpoints WHERE pool_id = $1"
        else:
            query = "SELECT id FROM endpoints WHERE pool_id = ?"
        
        rows = await self.db.fetch(query, pool_id)
        return [row[0] if isinstance(row, tuple) else row['id'] for row in rows]
    
    def _row_to_pool(self, row: Dict[str, Any]) -> PackagePool:
        """Convert database row to PackagePool object."""
        if isinstance(row, tuple):
            # Handle tuple format (some database drivers)
            row = {
                'id': row[0], 'name': row[1], 'description': row[2],
                'target_state_id': row[3], 'sync_policy': row[4],
                'created_at': row[5], 'updated_at': row[6]
            }
        
        # Parse sync policy
        sync_policy_data = json.loads(row['sync_policy']) if row['sync_policy'] else {}
        sync_policy = SyncPolicy(
            auto_sync=sync_policy_data.get('auto_sync', False),
            exclude_packages=sync_policy_data.get('exclude_packages', []),
            include_aur=sync_policy_data.get('include_aur', False),
            conflict_resolution=ConflictResolution(
                sync_policy_data.get('conflict_resolution', 'manual')
            )
        )
        
        # Parse timestamps
        created_at = row['created_at']
        updated_at = row['updated_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        
        return PackagePool(
            id=row['id'],
            name=row['name'],
            description=row['description'] or '',
            target_state_id=row['target_state_id'],
            sync_policy=sync_policy,
            created_at=created_at,
            updated_at=updated_at
        )


class EndpointRepository:
    """Repository for Endpoint operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create(self, endpoint: Endpoint) -> Endpoint:
        """Create a new endpoint."""
        # Validate endpoint data
        if not endpoint.name.strip():
            raise ValidationError("Endpoint name cannot be empty")
        if not endpoint.hostname.strip():
            raise ValidationError("Endpoint hostname cannot be empty")
        
        # Check for duplicate name/hostname combination
        existing = await self.get_by_name_hostname(endpoint.name, endpoint.hostname)
        if existing:
            raise ValidationError(f"Endpoint with name '{endpoint.name}' and hostname '{endpoint.hostname}' already exists")
        
        if self.db.database_type == "postgresql":
            query = """
                INSERT INTO endpoints (id, name, hostname, pool_id, last_seen, sync_status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
            """
            row = await self.db.fetchrow(
                query, endpoint.id, endpoint.name, endpoint.hostname,
                endpoint.pool_id, endpoint.last_seen, endpoint.sync_status.value,
                endpoint.created_at, endpoint.updated_at
            )
        else:  # SQLite
            query = """
                INSERT INTO endpoints (id, name, hostname, pool_id, last_seen, sync_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            last_seen_str = endpoint.last_seen.isoformat() if endpoint.last_seen else None
            await self.db.execute(
                query, endpoint.id, endpoint.name, endpoint.hostname,
                endpoint.pool_id, last_seen_str, endpoint.sync_status.value,
                endpoint.created_at.isoformat(), endpoint.updated_at.isoformat()
            )
            row = await self.db.fetchrow("SELECT * FROM endpoints WHERE id = ?", endpoint.id)
        
        return self._row_to_endpoint(row)
    
    async def get_by_id(self, endpoint_id: str) -> Optional[Endpoint]:
        """Get an endpoint by ID."""
        if self.db.database_type == "postgresql":
            query = "SELECT * FROM endpoints WHERE id = $1"
        else:
            query = "SELECT * FROM endpoints WHERE id = ?"
        
        row = await self.db.fetchrow(query, endpoint_id)
        return self._row_to_endpoint(row) if row else None
    
    async def get_by_name_hostname(self, name: str, hostname: str) -> Optional[Endpoint]:
        """Get an endpoint by name and hostname."""
        if self.db.database_type == "postgresql":
            query = "SELECT * FROM endpoints WHERE name = $1 AND hostname = $2"
        else:
            query = "SELECT * FROM endpoints WHERE name = ? AND hostname = ?"
        
        row = await self.db.fetchrow(query, name, hostname)
        return self._row_to_endpoint(row) if row else None
    
    async def list_by_pool(self, pool_id: Optional[str] = None) -> List[Endpoint]:
        """List endpoints, optionally filtered by pool."""
        if pool_id:
            if self.db.database_type == "postgresql":
                query = "SELECT * FROM endpoints WHERE pool_id = $1 ORDER BY created_at"
            else:
                query = "SELECT * FROM endpoints WHERE pool_id = ? ORDER BY created_at"
            rows = await self.db.fetch(query, pool_id)
        else:
            query = "SELECT * FROM endpoints ORDER BY created_at"
            rows = await self.db.fetch(query)
        
        return [self._row_to_endpoint(row) for row in rows]
    
    async def update_status(self, endpoint_id: str, status: SyncStatus) -> bool:
        """Update endpoint sync status."""
        endpoint = await self.get_by_id(endpoint_id)
        if not endpoint:
            return False
        
        if self.db.database_type == "postgresql":
            query = "UPDATE endpoints SET sync_status = $2, updated_at = $3 WHERE id = $1"
            await self.db.execute(query, endpoint_id, status.value, datetime.now())
        else:
            query = "UPDATE endpoints SET sync_status = ?, updated_at = ? WHERE id = ?"
            now = datetime.now()
            await self.db.execute(query, status.value, now.isoformat(), endpoint_id)
        return True
    
    async def update_last_seen(self, endpoint_id: str, timestamp: datetime) -> bool:
        """Update endpoint last seen timestamp."""
        endpoint = await self.get_by_id(endpoint_id)
        if not endpoint:
            return False
        
        if self.db.database_type == "postgresql":
            query = "UPDATE endpoints SET last_seen = $2, updated_at = $3 WHERE id = $1"
            await self.db.execute(query, endpoint_id, timestamp, datetime.now())
        else:
            query = "UPDATE endpoints SET last_seen = ?, updated_at = ? WHERE id = ?"
            now = datetime.now()
            await self.db.execute(query, timestamp.isoformat(), now.isoformat(), endpoint_id)
        return True
    
    async def assign_to_pool(self, endpoint_id: str, pool_id: str) -> bool:
        """Assign endpoint to a pool."""
        endpoint = await self.get_by_id(endpoint_id)
        if not endpoint:
            return False
        
        if self.db.database_type == "postgresql":
            query = "UPDATE endpoints SET pool_id = $2, updated_at = $3 WHERE id = $1"
            await self.db.execute(query, endpoint_id, pool_id, datetime.now())
        else:
            query = "UPDATE endpoints SET pool_id = ?, updated_at = ? WHERE id = ?"
            now = datetime.now()
            await self.db.execute(query, pool_id, now.isoformat(), endpoint_id)
        return True
    
    async def remove_from_pool(self, endpoint_id: str) -> bool:
        """Remove endpoint from its pool."""
        endpoint = await self.get_by_id(endpoint_id)
        if not endpoint:
            return False
        
        if self.db.database_type == "postgresql":
            query = "UPDATE endpoints SET pool_id = NULL, updated_at = $2 WHERE id = $1"
            await self.db.execute(query, endpoint_id, datetime.now())
        else:
            query = "UPDATE endpoints SET pool_id = NULL, updated_at = ? WHERE id = ?"
            now = datetime.now()
            await self.db.execute(query, now.isoformat(), endpoint_id)
        return True
    
    async def delete(self, endpoint_id: str) -> bool:
        """Delete an endpoint."""
        endpoint = await self.get_by_id(endpoint_id)
        if not endpoint:
            return False
        
        if self.db.database_type == "postgresql":
            query = "DELETE FROM endpoints WHERE id = $1"
        else:
            query = "DELETE FROM endpoints WHERE id = ?"
        
        await self.db.execute(query, endpoint_id)
        return True
    
    def _row_to_endpoint(self, row: Dict[str, Any]) -> Endpoint:
        """Convert database row to Endpoint object."""
        if isinstance(row, tuple):
            row = {
                'id': row[0], 'name': row[1], 'hostname': row[2],
                'pool_id': row[3], 'last_seen': row[4], 'sync_status': row[5],
                'created_at': row[6], 'updated_at': row[7]
            }
        
        # Parse timestamps
        last_seen = None
        if row['last_seen']:
            if isinstance(row['last_seen'], str):
                last_seen = datetime.fromisoformat(row['last_seen'].replace('Z', '+00:00'))
            else:
                last_seen = row['last_seen']
        
        created_at = row['created_at']
        updated_at = row['updated_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        
        return Endpoint(
            id=row['id'],
            name=row['name'],
            hostname=row['hostname'],
            pool_id=row['pool_id'],
            last_seen=last_seen,
            sync_status=SyncStatus(row['sync_status']),
            created_at=created_at,
            updated_at=updated_at
        )


class PackageStateRepository:
    """Repository for SystemState operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def save_state(self, pool_id: str, endpoint_id: str, state: SystemState) -> str:
        """Save a system state snapshot."""
        state_id = str(uuid4())
        
        # Serialize package data
        packages_data = []
        for pkg in state.packages:
            packages_data.append({
                'package_name': pkg.package_name,
                'version': pkg.version,
                'repository': pkg.repository,
                'installed_size': pkg.installed_size,
                'dependencies': pkg.dependencies
            })
        
        state_data = {
            'endpoint_id': state.endpoint_id,
            'timestamp': state.timestamp.isoformat(),
            'packages': packages_data,
            'pacman_version': state.pacman_version,
            'architecture': state.architecture
        }
        
        if self.db.database_type == "postgresql":
            query = """
                INSERT INTO package_states (id, pool_id, endpoint_id, state_data, pacman_version, architecture, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """
            result = await self.db.fetchval(
                query, state_id, pool_id, endpoint_id, json.dumps(state_data),
                state.pacman_version, state.architecture, datetime.now()
            )
        else:  # SQLite
            query = """
                INSERT INTO package_states (id, pool_id, endpoint_id, state_data, pacman_version, architecture, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            await self.db.execute(
                query, state_id, pool_id, endpoint_id, json.dumps(state_data),
                state.pacman_version, state.architecture, datetime.now().isoformat()
            )
            result = state_id
        
        return result
    
    async def get_state(self, state_id: str) -> Optional[SystemState]:
        """Get a system state by ID."""
        if self.db.database_type == "postgresql":
            query = "SELECT * FROM package_states WHERE id = $1"
        else:
            query = "SELECT * FROM package_states WHERE id = ?"
        
        row = await self.db.fetchrow(query, state_id)
        return self._row_to_system_state(row) if row else None
    
    async def get_latest_target_state(self, pool_id: str) -> Optional[SystemState]:
        """Get the latest target state for a pool."""
        if self.db.database_type == "postgresql":
            query = """
                SELECT ps.* FROM package_states ps
                JOIN pools p ON p.target_state_id = ps.id
                WHERE p.id = $1
            """
        else:
            query = """
                SELECT ps.* FROM package_states ps
                JOIN pools p ON p.target_state_id = ps.id
                WHERE p.id = ?
            """
        
        row = await self.db.fetchrow(query, pool_id)
        return self._row_to_system_state(row) if row else None
    
    async def get_endpoint_states(self, endpoint_id: str, limit: int = 10) -> List[SystemState]:
        """Get historical states for an endpoint."""
        if self.db.database_type == "postgresql":
            query = """
                SELECT * FROM package_states 
                WHERE endpoint_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """
        else:
            query = """
                SELECT * FROM package_states 
                WHERE endpoint_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """
        
        rows = await self.db.fetch(query, endpoint_id, limit)
        return [self._row_to_system_state(row) for row in rows]
    
    async def set_target_state(self, pool_id: str, state_id: str) -> bool:
        """Set a state as the target for a pool."""
        # Verify state exists
        state = await self.get_state(state_id)
        if not state:
            return False
        
        # Update pool's target_state_id
        if self.db.database_type == "postgresql":
            query = "UPDATE pools SET target_state_id = $2, updated_at = $3 WHERE id = $1"
            await self.db.execute(query, pool_id, state_id, datetime.now())
        else:
            query = "UPDATE pools SET target_state_id = ?, updated_at = ? WHERE id = ?"
            now = datetime.now()
            await self.db.execute(query, state_id, now.isoformat(), pool_id)
        return True
    
    def _row_to_system_state(self, row: Dict[str, Any]) -> SystemState:
        """Convert database row to SystemState object."""
        if isinstance(row, tuple):
            row = {
                'id': row[0], 'pool_id': row[1], 'endpoint_id': row[2],
                'state_data': row[3], 'is_target': row[4],
                'pacman_version': row[5], 'architecture': row[6], 'created_at': row[7]
            }
        
        # Parse state data
        state_data = json.loads(row['state_data'])
        
        # Convert packages
        packages = []
        for pkg_data in state_data['packages']:
            packages.append(PackageState(
                package_name=pkg_data['package_name'],
                version=pkg_data['version'],
                repository=pkg_data['repository'],
                installed_size=pkg_data['installed_size'],
                dependencies=pkg_data.get('dependencies', [])
            ))
        
        # Parse timestamp
        timestamp = datetime.fromisoformat(state_data['timestamp'].replace('Z', '+00:00'))
        
        return SystemState(
            endpoint_id=state_data['endpoint_id'],
            timestamp=timestamp,
            packages=packages,
            pacman_version=state_data['pacman_version'],
            architecture=state_data['architecture']
        )


class SyncOperationRepository:
    """Repository for SyncOperation operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create(self, operation: SyncOperation) -> SyncOperation:
        """Create a new sync operation."""
        if self.db.database_type == "postgresql":
            query = """
                INSERT INTO sync_operations (id, pool_id, endpoint_id, operation_type, status, details, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
            """
            row = await self.db.fetchrow(
                query, operation.id, operation.pool_id, operation.endpoint_id,
                operation.operation_type.value, operation.status.value,
                json.dumps(operation.details), operation.created_at
            )
        else:  # SQLite
            query = """
                INSERT INTO sync_operations (id, pool_id, endpoint_id, operation_type, status, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            await self.db.execute(
                query, operation.id, operation.pool_id, operation.endpoint_id,
                operation.operation_type.value, operation.status.value,
                json.dumps(operation.details), operation.created_at.isoformat()
            )
            row = await self.db.fetchrow("SELECT * FROM sync_operations WHERE id = ?", operation.id)
        
        return self._row_to_sync_operation(row)
    
    async def get_by_id(self, operation_id: str) -> Optional[SyncOperation]:
        """Get a sync operation by ID."""
        if self.db.database_type == "postgresql":
            query = "SELECT * FROM sync_operations WHERE id = $1"
        else:
            query = "SELECT * FROM sync_operations WHERE id = ?"
        
        row = await self.db.fetchrow(query, operation_id)
        return self._row_to_sync_operation(row) if row else None
    
    async def update_status(self, operation_id: str, status: OperationStatus, 
                          error_message: Optional[str] = None) -> bool:
        """Update operation status."""
        operation = await self.get_by_id(operation_id)
        if not operation:
            return False
        
        completed_at = datetime.now() if status in [OperationStatus.COMPLETED, OperationStatus.FAILED] else None
        
        if self.db.database_type == "postgresql":
            query = """
                UPDATE sync_operations 
                SET status = $2, error_message = $3, completed_at = $4
                WHERE id = $1
            """
            await self.db.execute(query, operation_id, status.value, error_message, completed_at)
        else:
            query = """
                UPDATE sync_operations 
                SET status = ?, error_message = ?, completed_at = ?
                WHERE id = ?
            """
            completed_at_str = completed_at.isoformat() if completed_at else None
            await self.db.execute(query, status.value, error_message, completed_at_str, operation_id)
        return True
    
    async def list_by_endpoint(self, endpoint_id: str, limit: int = 50) -> List[SyncOperation]:
        """List operations for an endpoint."""
        if self.db.database_type == "postgresql":
            query = """
                SELECT * FROM sync_operations 
                WHERE endpoint_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """
        else:
            query = """
                SELECT * FROM sync_operations 
                WHERE endpoint_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """
        
        rows = await self.db.fetch(query, endpoint_id, limit)
        return [self._row_to_sync_operation(row) for row in rows]
    
    async def list_by_pool(self, pool_id: str, limit: int = 50) -> List[SyncOperation]:
        """List operations for a pool."""
        if self.db.database_type == "postgresql":
            query = """
                SELECT * FROM sync_operations 
                WHERE pool_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """
        else:
            query = """
                SELECT * FROM sync_operations 
                WHERE pool_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """
        
        rows = await self.db.fetch(query, pool_id, limit)
        return [self._row_to_sync_operation(row) for row in rows]
    
    def _row_to_sync_operation(self, row: Dict[str, Any]) -> SyncOperation:
        """Convert database row to SyncOperation object."""
        if isinstance(row, tuple):
            row = {
                'id': row[0], 'pool_id': row[1], 'endpoint_id': row[2],
                'operation_type': row[3], 'status': row[4], 'details': row[5],
                'error_message': row[6], 'created_at': row[7], 'completed_at': row[8]
            }
        
        # Parse details
        details = json.loads(row['details']) if row['details'] else {}
        
        # Parse timestamps
        created_at = row['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        completed_at = None
        if row['completed_at']:
            if isinstance(row['completed_at'], str):
                completed_at = datetime.fromisoformat(row['completed_at'].replace('Z', '+00:00'))
            else:
                completed_at = row['completed_at']
        
        return SyncOperation(
            id=row['id'],
            pool_id=row['pool_id'],
            endpoint_id=row['endpoint_id'],
            operation_type=OperationType(row['operation_type']),
            status=OperationStatus(row['status']),
            details=details,
            created_at=created_at,
            completed_at=completed_at,
            error_message=row['error_message']
        )


class RepositoryRepository:
    """Repository for Repository operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create_or_update(self, repository: Repository) -> Repository:
        """Create or update repository information."""
        # Check if repository exists
        existing = await self.get_by_endpoint_and_name(repository.endpoint_id, repository.repo_name)
        
        # Serialize packages
        packages_data = []
        for pkg in repository.packages:
            packages_data.append({
                'name': pkg.name,
                'version': pkg.version,
                'repository': pkg.repository,
                'architecture': pkg.architecture,
                'description': pkg.description
            })
        
        if existing:
            # Update existing
            if self.db.database_type == "postgresql":
                query = """
                    UPDATE repositories 
                    SET repo_url = $3, packages = $4, last_updated = $5
                    WHERE endpoint_id = $1 AND repo_name = $2
                    RETURNING *
                """
                row = await self.db.fetchrow(
                    query, repository.endpoint_id, repository.repo_name,
                    repository.repo_url, json.dumps(packages_data), repository.last_updated
                )
            else:  # SQLite
                query = """
                    UPDATE repositories 
                    SET repo_url = ?, packages = ?, last_updated = ?
                    WHERE endpoint_id = ? AND repo_name = ?
                """
                await self.db.execute(
                    query, repository.repo_url, json.dumps(packages_data),
                    repository.last_updated.isoformat(), repository.endpoint_id, repository.repo_name
                )
                row = await self.db.fetchrow(
                    "SELECT * FROM repositories WHERE endpoint_id = ? AND repo_name = ?",
                    repository.endpoint_id, repository.repo_name
                )
        else:
            # Create new
            if self.db.database_type == "postgresql":
                query = """
                    INSERT INTO repositories (id, endpoint_id, repo_name, repo_url, packages, last_updated)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING *
                """
                row = await self.db.fetchrow(
                    query, repository.id, repository.endpoint_id, repository.repo_name,
                    repository.repo_url, json.dumps(packages_data), repository.last_updated
                )
            else:  # SQLite
                query = """
                    INSERT INTO repositories (id, endpoint_id, repo_name, repo_url, packages, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                await self.db.execute(
                    query, repository.id, repository.endpoint_id, repository.repo_name,
                    repository.repo_url, json.dumps(packages_data), repository.last_updated.isoformat()
                )
                row = await self.db.fetchrow("SELECT * FROM repositories WHERE id = ?", repository.id)
        
        return self._row_to_repository(row)
    
    async def get_by_endpoint_and_name(self, endpoint_id: str, repo_name: str) -> Optional[Repository]:
        """Get repository by endpoint and name."""
        if self.db.database_type == "postgresql":
            query = "SELECT * FROM repositories WHERE endpoint_id = $1 AND repo_name = $2"
        else:
            query = "SELECT * FROM repositories WHERE endpoint_id = ? AND repo_name = ?"
        
        row = await self.db.fetchrow(query, endpoint_id, repo_name)
        return self._row_to_repository(row) if row else None
    
    async def list_by_endpoint(self, endpoint_id: str) -> List[Repository]:
        """List repositories for an endpoint."""
        if self.db.database_type == "postgresql":
            query = "SELECT * FROM repositories WHERE endpoint_id = $1 ORDER BY repo_name"
        else:
            query = "SELECT * FROM repositories WHERE endpoint_id = ? ORDER BY repo_name"
        
        rows = await self.db.fetch(query, endpoint_id)
        return [self._row_to_repository(row) for row in rows]
    
    async def delete_by_endpoint(self, endpoint_id: str) -> bool:
        """Delete all repositories for an endpoint."""
        if self.db.database_type == "postgresql":
            query = "DELETE FROM repositories WHERE endpoint_id = $1"
        else:
            query = "DELETE FROM repositories WHERE endpoint_id = ?"
        
        await self.db.execute(query, endpoint_id)
        return True
    
    def _row_to_repository(self, row: Dict[str, Any]) -> Repository:
        """Convert database row to Repository object."""
        if isinstance(row, tuple):
            row = {
                'id': row[0], 'endpoint_id': row[1], 'repo_name': row[2],
                'repo_url': row[3], 'packages': row[4], 'last_updated': row[5]
            }
        
        # Parse packages
        packages_data = json.loads(row['packages']) if row['packages'] else []
        packages = []
        for pkg_data in packages_data:
            packages.append(RepositoryPackage(
                name=pkg_data['name'],
                version=pkg_data['version'],
                repository=pkg_data['repository'],
                architecture=pkg_data['architecture'],
                description=pkg_data.get('description')
            ))
        
        # Parse timestamp
        last_updated = row['last_updated']
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        
        return Repository(
            id=row['id'],
            endpoint_id=row['endpoint_id'],
            repo_name=row['repo_name'],
            repo_url=row['repo_url'],
            packages=packages,
            last_updated=last_updated
        )


class ORMManager:
    """Main ORM manager that provides access to all repositories."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.pools = PoolRepository(db_manager)
        self.endpoints = EndpointRepository(db_manager)
        self.package_states = PackageStateRepository(db_manager)
        self.sync_operations = SyncOperationRepository(db_manager)
        self.repositories = RepositoryRepository(db_manager)