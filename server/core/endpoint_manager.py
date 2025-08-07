"""
Endpoint Manager for the Pacman Sync Utility.

This module provides endpoint management functionality including registration,
status updates, authentication, and repository information processing.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from jose import jwt, JWTError
import secrets
import hashlib

from shared.models import Endpoint, Repository, SyncStatus
from shared.interfaces import IEndpointManager
from server.database.connection import DatabaseManager
from server.database.orm import ORMManager

logger = logging.getLogger(__name__)


class EndpointAuthenticationError(Exception):
    """Raised when endpoint authentication fails."""
    pass


class EndpointManager(IEndpointManager):
    """Manages endpoint registration, authentication, and status updates."""
    
    def __init__(self, db_manager: DatabaseManager, jwt_secret: str = None, jwt_expiration_hours: int = 24 * 30):
        self.db = db_manager
        self.orm = ORMManager(db_manager)
        self.jwt_secret = jwt_secret or secrets.token_urlsafe(32)
        self.jwt_expiration_hours = jwt_expiration_hours
        
    async def register_endpoint(self, name: str, hostname: str) -> Endpoint:
        """Register a new endpoint."""
        logger.info(f"Registering endpoint: {name}@{hostname}")
        
        # Check if endpoint already exists
        existing = await self.orm.endpoints.get_by_name_hostname(name, hostname)
        if existing:
            logger.info(f"Endpoint {name}@{hostname} already exists, updating last_seen")
            await self.update_last_seen(existing.id, datetime.now())
            return existing
        
        # Create new endpoint
        endpoint = Endpoint(
            id="",  # Will be generated in __post_init__
            name=name,
            hostname=hostname,
            sync_status=SyncStatus.OFFLINE
        )
        
        created_endpoint = await self.orm.endpoints.create(endpoint)
        logger.info(f"Successfully registered endpoint: {created_endpoint.id}")
        return created_endpoint
    
    async def get_endpoint(self, endpoint_id: str) -> Optional[Endpoint]:
        """Get an endpoint by ID."""
        return await self.orm.endpoints.get_by_id(endpoint_id)
    
    async def list_endpoints(self, pool_id: Optional[str] = None) -> List[Endpoint]:
        """List endpoints, optionally filtered by pool."""
        return await self.orm.endpoints.list_by_pool(pool_id)
    
    async def update_endpoint_status(self, endpoint_id: str, status: SyncStatus) -> bool:
        """Update endpoint sync status."""
        logger.info(f"Updating endpoint {endpoint_id} status to {status.value}")
        success = await self.orm.endpoints.update_status(endpoint_id, status)
        if success:
            await self.update_last_seen(endpoint_id, datetime.now())
        return success
    
    async def update_last_seen(self, endpoint_id: str, timestamp: datetime) -> bool:
        """Update endpoint last seen timestamp."""
        return await self.orm.endpoints.update_last_seen(endpoint_id, timestamp)
    
    async def remove_endpoint(self, endpoint_id: str) -> bool:
        """Remove an endpoint."""
        logger.info(f"Removing endpoint: {endpoint_id}")
        
        # Remove repository information first
        await self.orm.repositories.delete_by_endpoint(endpoint_id)
        
        # Remove endpoint
        success = await self.orm.endpoints.delete(endpoint_id)
        if success:
            logger.info(f"Successfully removed endpoint: {endpoint_id}")
        return success
    
    async def assign_to_pool(self, endpoint_id: str, pool_id: str) -> bool:
        """Assign endpoint to a pool."""
        logger.info(f"Assigning endpoint {endpoint_id} to pool {pool_id}")
        return await self.orm.endpoints.assign_to_pool(endpoint_id, pool_id)
    
    async def remove_from_pool(self, endpoint_id: str) -> bool:
        """Remove endpoint from its pool."""
        logger.info(f"Removing endpoint {endpoint_id} from pool")
        return await self.orm.endpoints.remove_from_pool(endpoint_id)
    
    async def update_repository_info(self, endpoint_id: str, repositories: List[Repository]) -> bool:
        """Update repository information for an endpoint."""
        logger.info(f"Updating repository info for endpoint {endpoint_id}")
        
        # Verify endpoint exists
        endpoint = await self.get_endpoint(endpoint_id)
        if not endpoint:
            logger.error(f"Endpoint {endpoint_id} not found")
            return False
        
        try:
            # Remove existing repository information
            await self.orm.repositories.delete_by_endpoint(endpoint_id)
            
            # Add new repository information
            for repo in repositories:
                repo.endpoint_id = endpoint_id  # Ensure correct endpoint_id
                await self.orm.repositories.create_or_update(repo)
            
            # Update endpoint last_seen
            await self.update_last_seen(endpoint_id, datetime.now())
            
            logger.info(f"Successfully updated repository info for endpoint {endpoint_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update repository info for endpoint {endpoint_id}: {e}")
            return False
    
    async def get_repository_info(self, endpoint_id: str) -> List[Repository]:
        """Get repository information for an endpoint."""
        return await self.orm.repositories.list_by_endpoint(endpoint_id)
    
    def generate_auth_token(self, endpoint_id: str, endpoint_name: str) -> str:
        """Generate JWT authentication token for an endpoint."""
        payload = {
            'endpoint_id': endpoint_id,
            'endpoint_name': endpoint_name,
            'issued_at': datetime.now().timestamp(),
            'expires_at': (datetime.now().timestamp() + 3600 * self.jwt_expiration_hours)
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def verify_auth_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT authentication token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Check expiration
            if payload.get('expires_at', 0) < datetime.now().timestamp():
                raise EndpointAuthenticationError("Token expired")
            
            return payload
            
        except JWTError as e:
            raise EndpointAuthenticationError(f"Invalid token: {e}")
    
    async def authenticate_endpoint(self, token: str) -> Optional[Endpoint]:
        """Authenticate endpoint using JWT token."""
        try:
            payload = self.verify_auth_token(token)
            endpoint_id = payload.get('endpoint_id')
            
            if not endpoint_id:
                raise EndpointAuthenticationError("Token missing endpoint_id")
            
            endpoint = await self.get_endpoint(endpoint_id)
            if not endpoint:
                raise EndpointAuthenticationError("Endpoint not found")
            
            return endpoint
            
        except EndpointAuthenticationError:
            raise
        except Exception as e:
            raise EndpointAuthenticationError(f"Authentication failed: {e}")
    
    async def get_endpoint_by_name_hostname(self, name: str, hostname: str) -> Optional[Endpoint]:
        """Get endpoint by name and hostname combination."""
        return await self.orm.endpoints.get_by_name_hostname(name, hostname)