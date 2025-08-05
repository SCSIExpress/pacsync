"""
Package Pool Management Service for the Pacman Sync Utility.

This module implements the PackagePoolManager class that handles pool creation,
modification, deletion, endpoint assignment, and synchronization coordination.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from shared.models import (
    PackagePool, Endpoint, SyncStatus, SyncPolicy, ConflictResolution
)
from shared.interfaces import IPackagePoolManager
from server.database.orm import PoolRepository, EndpointRepository, ValidationError, NotFoundError
from server.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class PoolStatusInfo:
    """Information about pool status and endpoint synchronization."""
    
    def __init__(self, pool: PackagePool, endpoints: List[Endpoint]):
        self.pool = pool
        self.endpoints = endpoints
        self.total_endpoints = len(endpoints)
        self.in_sync_count = len([e for e in endpoints if e.sync_status == SyncStatus.IN_SYNC])
        self.ahead_count = len([e for e in endpoints if e.sync_status == SyncStatus.AHEAD])
        self.behind_count = len([e for e in endpoints if e.sync_status == SyncStatus.BEHIND])
        self.offline_count = len([e for e in endpoints if e.sync_status == SyncStatus.OFFLINE])
    
    @property
    def sync_percentage(self) -> float:
        """Calculate percentage of endpoints that are in sync."""
        if self.total_endpoints == 0:
            return 100.0
        return (self.in_sync_count / self.total_endpoints) * 100.0
    
    @property
    def overall_status(self) -> str:
        """Get overall pool synchronization status."""
        if self.total_endpoints == 0:
            return "empty"
        elif self.in_sync_count == self.total_endpoints:
            return "fully_synced"
        elif self.offline_count == self.total_endpoints:
            return "all_offline"
        elif self.in_sync_count > 0:
            return "partially_synced"
        else:
            return "out_of_sync"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "pool_id": self.pool.id,
            "pool_name": self.pool.name,
            "total_endpoints": self.total_endpoints,
            "in_sync_count": self.in_sync_count,
            "ahead_count": self.ahead_count,
            "behind_count": self.behind_count,
            "offline_count": self.offline_count,
            "sync_percentage": self.sync_percentage,
            "overall_status": self.overall_status,
            "has_target_state": self.pool.target_state_id is not None,
            "auto_sync_enabled": self.pool.sync_policy.auto_sync
        }


class PackagePoolManager(IPackagePoolManager):
    """
    Manages package pools including creation, modification, deletion,
    endpoint assignment, and synchronization coordination.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.pool_repo = PoolRepository(db_manager)
        self.endpoint_repo = EndpointRepository(db_manager)
        logger.info("PackagePoolManager initialized")
    
    async def create_pool(self, name: str, description: str = "", 
                         sync_policy: Optional[SyncPolicy] = None) -> PackagePool:
        """
        Create a new package pool.
        
        Args:
            name: Pool name (must be unique)
            description: Optional pool description
            sync_policy: Optional synchronization policy
            
        Returns:
            Created PackagePool object
            
        Raises:
            ValidationError: If pool name is invalid or already exists
        """
        logger.info(f"Creating new pool: {name}")
        
        if not name or not name.strip():
            raise ValidationError("Pool name cannot be empty")
        
        # Use default sync policy if none provided
        if sync_policy is None:
            sync_policy = SyncPolicy()
        
        # Create pool object
        pool = PackagePool(
            id=str(uuid4()),
            name=name.strip(),
            description=description.strip() if description else "",
            sync_policy=sync_policy,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        try:
            created_pool = await self.pool_repo.create(pool)
            logger.info(f"Successfully created pool: {created_pool.id} ({created_pool.name})")
            return created_pool
        except ValidationError as e:
            logger.error(f"Failed to create pool '{name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating pool '{name}': {e}")
            raise ValidationError(f"Failed to create pool: {str(e)}")
    
    async def get_pool(self, pool_id: str) -> Optional[PackagePool]:
        """
        Get a package pool by ID.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            PackagePool object if found, None otherwise
        """
        if not pool_id:
            return None
        
        try:
            pool = await self.pool_repo.get_by_id(pool_id)
            if pool:
                # Update endpoints list
                pool.endpoints = await self.pool_repo.get_endpoints(pool_id)
            return pool
        except Exception as e:
            logger.error(f"Error retrieving pool {pool_id}: {e}")
            return None
    
    async def get_pool_by_name(self, name: str) -> Optional[PackagePool]:
        """
        Get a package pool by name.
        
        Args:
            name: Pool name
            
        Returns:
            PackagePool object if found, None otherwise
        """
        if not name:
            return None
        
        try:
            pool = await self.pool_repo.get_by_name(name)
            if pool:
                # Update endpoints list
                pool.endpoints = await self.pool_repo.get_endpoints(pool.id)
            return pool
        except Exception as e:
            logger.error(f"Error retrieving pool by name '{name}': {e}")
            return None
    
    async def list_pools(self) -> List[PackagePool]:
        """
        List all package pools.
        
        Returns:
            List of PackagePool objects
        """
        try:
            pools = await self.pool_repo.list_all()
            
            # Update endpoints list for each pool
            for pool in pools:
                pool.endpoints = await self.pool_repo.get_endpoints(pool.id)
            
            logger.debug(f"Retrieved {len(pools)} pools")
            return pools
        except Exception as e:
            logger.error(f"Error listing pools: {e}")
            return []
    
    async def update_pool(self, pool_id: str, **kwargs) -> PackagePool:
        """
        Update a package pool.
        
        Args:
            pool_id: Pool identifier
            **kwargs: Fields to update (name, description, sync_policy, target_state_id)
            
        Returns:
            Updated PackagePool object
            
        Raises:
            NotFoundError: If pool doesn't exist
            ValidationError: If update data is invalid
        """
        logger.info(f"Updating pool: {pool_id}")
        
        if not pool_id:
            raise ValidationError("Pool ID cannot be empty")
        
        try:
            updated_pool = await self.pool_repo.update(pool_id, **kwargs)
            # Update endpoints list
            updated_pool.endpoints = await self.pool_repo.get_endpoints(pool_id)
            
            logger.info(f"Successfully updated pool: {pool_id}")
            return updated_pool
        except NotFoundError as e:
            logger.error(f"Pool not found for update: {pool_id}")
            raise
        except ValidationError as e:
            logger.error(f"Validation error updating pool {pool_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating pool {pool_id}: {e}")
            raise ValidationError(f"Failed to update pool: {str(e)}")
    
    async def delete_pool(self, pool_id: str) -> bool:
        """
        Delete a package pool.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            True if deleted successfully, False if pool not found
        """
        logger.info(f"Deleting pool: {pool_id}")
        
        if not pool_id:
            return False
        
        try:
            # First, remove all endpoints from the pool
            endpoints = await self.endpoint_repo.list_by_pool(pool_id)
            for endpoint in endpoints:
                await self.endpoint_repo.remove_from_pool(endpoint.id)
                logger.debug(f"Removed endpoint {endpoint.id} from pool {pool_id}")
            
            # Delete the pool
            success = await self.pool_repo.delete(pool_id)
            
            if success:
                logger.info(f"Successfully deleted pool: {pool_id}")
            else:
                logger.warning(f"Pool not found for deletion: {pool_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error deleting pool {pool_id}: {e}")
            return False
    
    async def assign_endpoint(self, pool_id: str, endpoint_id: str) -> bool:
        """
        Assign an endpoint to a pool.
        
        Args:
            pool_id: Pool identifier
            endpoint_id: Endpoint identifier
            
        Returns:
            True if assigned successfully, False otherwise
        """
        logger.info(f"Assigning endpoint {endpoint_id} to pool {pool_id}")
        
        if not pool_id or not endpoint_id:
            logger.error("Pool ID and endpoint ID cannot be empty")
            return False
        
        try:
            # Verify pool exists
            pool = await self.pool_repo.get_by_id(pool_id)
            if not pool:
                logger.error(f"Pool not found: {pool_id}")
                return False
            
            # Verify endpoint exists
            endpoint = await self.endpoint_repo.get_by_id(endpoint_id)
            if not endpoint:
                logger.error(f"Endpoint not found: {endpoint_id}")
                return False
            
            # Remove endpoint from current pool if assigned
            if endpoint.pool_id and endpoint.pool_id != pool_id:
                await self.endpoint_repo.remove_from_pool(endpoint_id)
                logger.debug(f"Removed endpoint {endpoint_id} from previous pool {endpoint.pool_id}")
            
            # Assign to new pool
            success = await self.endpoint_repo.assign_to_pool(endpoint_id, pool_id)
            
            if success:
                logger.info(f"Successfully assigned endpoint {endpoint_id} to pool {pool_id}")
                # Update endpoint sync status to reflect new pool assignment
                await self.endpoint_repo.update_status(endpoint_id, SyncStatus.BEHIND)
            else:
                logger.error(f"Failed to assign endpoint {endpoint_id} to pool {pool_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error assigning endpoint {endpoint_id} to pool {pool_id}: {e}")
            return False
    
    async def remove_endpoint(self, pool_id: str, endpoint_id: str) -> bool:
        """
        Remove an endpoint from a pool.
        
        Args:
            pool_id: Pool identifier
            endpoint_id: Endpoint identifier
            
        Returns:
            True if removed successfully, False otherwise
        """
        logger.info(f"Removing endpoint {endpoint_id} from pool {pool_id}")
        
        if not pool_id or not endpoint_id:
            logger.error("Pool ID and endpoint ID cannot be empty")
            return False
        
        try:
            # Verify endpoint is in the specified pool
            endpoint = await self.endpoint_repo.get_by_id(endpoint_id)
            if not endpoint:
                logger.error(f"Endpoint not found: {endpoint_id}")
                return False
            
            if endpoint.pool_id != pool_id:
                logger.warning(f"Endpoint {endpoint_id} is not in pool {pool_id}")
                return False
            
            # Remove from pool
            success = await self.endpoint_repo.remove_from_pool(endpoint_id)
            
            if success:
                logger.info(f"Successfully removed endpoint {endpoint_id} from pool {pool_id}")
                # Update endpoint sync status
                await self.endpoint_repo.update_status(endpoint_id, SyncStatus.OFFLINE)
            else:
                logger.error(f"Failed to remove endpoint {endpoint_id} from pool {pool_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error removing endpoint {endpoint_id} from pool {pool_id}: {e}")
            return False
    
    async def get_pool_status(self, pool_id: str) -> Optional[PoolStatusInfo]:
        """
        Get detailed status information for a pool.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            PoolStatusInfo object with detailed status, None if pool not found
        """
        try:
            pool = await self.get_pool(pool_id)
            if not pool:
                return None
            
            endpoints = await self.endpoint_repo.list_by_pool(pool_id)
            return PoolStatusInfo(pool, endpoints)
        except Exception as e:
            logger.error(f"Error getting pool status for {pool_id}: {e}")
            return None
    
    async def list_pool_statuses(self) -> List[PoolStatusInfo]:
        """
        Get status information for all pools.
        
        Returns:
            List of PoolStatusInfo objects
        """
        try:
            pools = await self.list_pools()
            statuses = []
            
            for pool in pools:
                endpoints = await self.endpoint_repo.list_by_pool(pool.id)
                statuses.append(PoolStatusInfo(pool, endpoints))
            
            return statuses
        except Exception as e:
            logger.error(f"Error listing pool statuses: {e}")
            return []
    
    async def get_unassigned_endpoints(self) -> List[Endpoint]:
        """
        Get list of endpoints not assigned to any pool.
        
        Returns:
            List of unassigned Endpoint objects
        """
        try:
            all_endpoints = await self.endpoint_repo.list_by_pool(None)
            unassigned = [e for e in all_endpoints if e.pool_id is None]
            logger.debug(f"Found {len(unassigned)} unassigned endpoints")
            return unassigned
        except Exception as e:
            logger.error(f"Error getting unassigned endpoints: {e}")
            return []
    
    async def move_endpoint_to_pool(self, endpoint_id: str, from_pool_id: str, to_pool_id: str) -> bool:
        """
        Move an endpoint from one pool to another.
        
        Args:
            endpoint_id: Endpoint identifier
            from_pool_id: Source pool identifier
            to_pool_id: Destination pool identifier
            
        Returns:
            True if moved successfully, False otherwise
        """
        logger.info(f"Moving endpoint {endpoint_id} from pool {from_pool_id} to pool {to_pool_id}")
        
        try:
            # Remove from source pool
            if not await self.remove_endpoint(from_pool_id, endpoint_id):
                return False
            
            # Assign to destination pool
            return await self.assign_endpoint(to_pool_id, endpoint_id)
        except Exception as e:
            logger.error(f"Error moving endpoint {endpoint_id}: {e}")
            return False
    
    async def update_sync_policy(self, pool_id: str, sync_policy: SyncPolicy) -> bool:
        """
        Update synchronization policy for a pool.
        
        Args:
            pool_id: Pool identifier
            sync_policy: New synchronization policy
            
        Returns:
            True if updated successfully, False otherwise
        """
        logger.info(f"Updating sync policy for pool {pool_id}")
        
        try:
            await self.update_pool(pool_id, sync_policy=sync_policy)
            logger.info(f"Successfully updated sync policy for pool {pool_id}")
            return True
        except (NotFoundError, ValidationError) as e:
            logger.error(f"Failed to update sync policy for pool {pool_id}: {e}")
            return False
    
    async def set_target_state(self, pool_id: str, state_id: str) -> bool:
        """
        Set the target state for a pool.
        
        Args:
            pool_id: Pool identifier
            state_id: State identifier to set as target
            
        Returns:
            True if set successfully, False otherwise
        """
        logger.info(f"Setting target state {state_id} for pool {pool_id}")
        
        try:
            await self.update_pool(pool_id, target_state_id=state_id)
            
            # Update all endpoints in the pool to "behind" status since they now have a new target
            endpoints = await self.endpoint_repo.list_by_pool(pool_id)
            for endpoint in endpoints:
                if endpoint.sync_status != SyncStatus.OFFLINE:
                    await self.endpoint_repo.update_status(endpoint.id, SyncStatus.BEHIND)
            
            logger.info(f"Successfully set target state {state_id} for pool {pool_id}")
            return True
        except (NotFoundError, ValidationError) as e:
            logger.error(f"Failed to set target state for pool {pool_id}: {e}")
            return False
    
    async def clear_target_state(self, pool_id: str) -> bool:
        """
        Clear the target state for a pool.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            True if cleared successfully, False otherwise
        """
        logger.info(f"Clearing target state for pool {pool_id}")
        
        try:
            await self.update_pool(pool_id, target_state_id=None)
            logger.info(f"Successfully cleared target state for pool {pool_id}")
            return True
        except (NotFoundError, ValidationError) as e:
            logger.error(f"Failed to clear target state for pool {pool_id}: {e}")
            return False