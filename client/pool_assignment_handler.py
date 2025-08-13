"""
Pool Assignment Handler for Pacman Sync Utility Client.

This module handles automatic actions when an endpoint is assigned to or removed from a pool.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

from client.repository_sync_client import RepositorySyncClient
from client.api_client import PacmanSyncAPIClient

logger = logging.getLogger(__name__)


class PoolAssignmentHandler:
    """
    Handles automatic actions when pool assignment changes.
    
    This handler:
    1. Detects when an endpoint is assigned to a pool
    2. Triggers full repository and package sync
    3. Ensures the server has complete data for pool analysis
    """
    
    def __init__(self, server_url: str, endpoint_name: str, hostname: Optional[str] = None):
        self.server_url = server_url
        self.endpoint_name = endpoint_name
        self.hostname = hostname
        self.last_pool_id: Optional[str] = None
        self.sync_in_progress = False
        
        logger.info(f"Pool assignment handler initialized for {endpoint_name}")
    
    async def handle_pool_assignment_change(
        self, 
        pool_id: Optional[str], 
        assigned: bool, 
        api_client: PacmanSyncAPIClient, 
        endpoint_id: str
    ) -> None:
        """
        Handle pool assignment changes.
        
        Args:
            pool_id: ID of the assigned pool (None if not assigned)
            assigned: Whether the endpoint is assigned to a pool
            api_client: Authenticated API client
            endpoint_id: ID of the endpoint
        """
        try:
            # Check if this is a new assignment (not just a status update)
            if assigned and pool_id and pool_id != self.last_pool_id:
                logger.info(f"Endpoint assigned to new pool: {pool_id}")
                
                # Prevent concurrent syncs
                if self.sync_in_progress:
                    logger.warning("Pool assignment sync already in progress, skipping")
                    return
                
                self.sync_in_progress = True
                
                try:
                    # Perform full repository and package sync
                    await self._perform_pool_assignment_sync(api_client, endpoint_id, pool_id)
                    
                    # Update last known pool ID
                    self.last_pool_id = pool_id
                    
                finally:
                    self.sync_in_progress = False
                    
            elif not assigned and self.last_pool_id:
                logger.info(f"Endpoint removed from pool: {self.last_pool_id}")
                self.last_pool_id = None
                
            elif assigned and pool_id == self.last_pool_id:
                logger.debug(f"Pool assignment unchanged: {pool_id}")
                
        except Exception as e:
            logger.error(f"Error handling pool assignment change: {e}")
            self.sync_in_progress = False
    
    async def _perform_pool_assignment_sync(
        self, 
        api_client: PacmanSyncAPIClient, 
        endpoint_id: str, 
        pool_id: str
    ) -> None:
        """
        Perform the actual sync when assigned to a pool.
        
        Args:
            api_client: Authenticated API client
            endpoint_id: ID of the endpoint
            pool_id: ID of the assigned pool
        """
        try:
            logger.info(f"Starting automatic sync for pool assignment to {pool_id}")
            
            # Create repository sync client
            sync_client = RepositorySyncClient(
                server_url=self.server_url,
                endpoint_name=self.endpoint_name,
                hostname=self.hostname
            )
            
            try:
                # Perform full sync using the existing authenticated API client
                success = await sync_client.perform_pool_assignment_sync(api_client, endpoint_id)
                
                if success:
                    logger.info(f"✅ Automatic sync completed successfully for pool {pool_id}")
                    
                    # Report success status
                    await self._report_sync_status(api_client, endpoint_id, "sync_completed")
                    
                else:
                    logger.error(f"❌ Automatic sync failed for pool {pool_id}")
                    
                    # Report failure status
                    await self._report_sync_status(api_client, endpoint_id, "sync_failed")
                    
            finally:
                # Don't close the API client as it's shared
                pass
                
        except Exception as e:
            logger.error(f"Failed to perform pool assignment sync: {e}")
            
            # Report error status
            try:
                await self._report_sync_status(api_client, endpoint_id, "sync_error")
            except:
                pass  # Don't fail if status reporting fails
    
    async def _report_sync_status(
        self, 
        api_client: PacmanSyncAPIClient, 
        endpoint_id: str, 
        status: str
    ) -> None:
        """
        Report sync status to the server.
        
        Args:
            api_client: Authenticated API client
            endpoint_id: ID of the endpoint
            status: Status to report
        """
        try:
            from shared.models import SyncStatus
            
            # Map string status to SyncStatus enum
            status_mapping = {
                "sync_completed": SyncStatus.IN_SYNC,
                "sync_failed": SyncStatus.OFFLINE,
                "sync_error": SyncStatus.OFFLINE
            }
            
            sync_status = status_mapping.get(status, SyncStatus.OFFLINE)
            
            # Report status to server
            await api_client.report_status(endpoint_id, sync_status)
            
            logger.debug(f"Reported sync status: {sync_status.value}")
            
        except Exception as e:
            logger.warning(f"Failed to report sync status: {e}")
    
    def get_last_pool_id(self) -> Optional[str]:
        """Get the last known pool ID."""
        return self.last_pool_id
    
    def is_sync_in_progress(self) -> bool:
        """Check if a sync is currently in progress."""
        return self.sync_in_progress