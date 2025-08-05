"""
Core interfaces for the Pacman Sync Utility.

This module defines the abstract interfaces that components must implement
to ensure consistent behavior across the system.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import (
    PackagePool, Endpoint, SystemState, SyncOperation, 
    CompatibilityAnalysis, Repository, OperationType, SyncStatus
)


class IPackagePoolManager(ABC):
    """Interface for managing package pools."""
    
    @abstractmethod
    async def create_pool(self, name: str, description: str) -> PackagePool:
        """Create a new package pool."""
        pass
    
    @abstractmethod
    async def get_pool(self, pool_id: str) -> Optional[PackagePool]:
        """Get a package pool by ID."""
        pass
    
    @abstractmethod
    async def list_pools(self) -> List[PackagePool]:
        """List all package pools."""
        pass
    
    @abstractmethod
    async def update_pool(self, pool_id: str, **kwargs) -> PackagePool:
        """Update a package pool."""
        pass
    
    @abstractmethod
    async def delete_pool(self, pool_id: str) -> bool:
        """Delete a package pool."""
        pass
    
    @abstractmethod
    async def assign_endpoint(self, pool_id: str, endpoint_id: str) -> bool:
        """Assign an endpoint to a pool."""
        pass
    
    @abstractmethod
    async def remove_endpoint(self, pool_id: str, endpoint_id: str) -> bool:
        """Remove an endpoint from a pool."""
        pass


class IEndpointManager(ABC):
    """Interface for managing endpoints."""
    
    @abstractmethod
    async def register_endpoint(self, name: str, hostname: str) -> Endpoint:
        """Register a new endpoint."""
        pass
    
    @abstractmethod
    async def get_endpoint(self, endpoint_id: str) -> Optional[Endpoint]:
        """Get an endpoint by ID."""
        pass
    
    @abstractmethod
    async def list_endpoints(self, pool_id: Optional[str] = None) -> List[Endpoint]:
        """List endpoints, optionally filtered by pool."""
        pass
    
    @abstractmethod
    async def update_endpoint_status(self, endpoint_id: str, status: SyncStatus) -> bool:
        """Update endpoint sync status."""
        pass
    
    @abstractmethod
    async def update_last_seen(self, endpoint_id: str, timestamp: datetime) -> bool:
        """Update endpoint last seen timestamp."""
        pass
    
    @abstractmethod
    async def remove_endpoint(self, endpoint_id: str) -> bool:
        """Remove an endpoint."""
        pass


class ISyncCoordinator(ABC):
    """Interface for coordinating synchronization operations."""
    
    @abstractmethod
    async def sync_to_latest(self, endpoint_id: str) -> SyncOperation:
        """Sync endpoint to latest pool state."""
        pass
    
    @abstractmethod
    async def set_as_latest(self, endpoint_id: str) -> SyncOperation:
        """Set endpoint's current state as pool's latest."""
        pass
    
    @abstractmethod
    async def revert_to_previous(self, endpoint_id: str) -> SyncOperation:
        """Revert endpoint to previous state."""
        pass
    
    @abstractmethod
    async def get_operation_status(self, operation_id: str) -> Optional[SyncOperation]:
        """Get status of a sync operation."""
        pass
    
    @abstractmethod
    async def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a pending sync operation."""
        pass


class IStateManager(ABC):
    """Interface for managing package states."""
    
    @abstractmethod
    async def save_state(self, endpoint_id: str, state: SystemState) -> str:
        """Save a system state snapshot."""
        pass
    
    @abstractmethod
    async def get_state(self, state_id: str) -> Optional[SystemState]:
        """Get a system state by ID."""
        pass
    
    @abstractmethod
    async def get_latest_state(self, pool_id: str) -> Optional[SystemState]:
        """Get the latest target state for a pool."""
        pass
    
    @abstractmethod
    async def get_endpoint_states(self, endpoint_id: str, limit: int = 10) -> List[SystemState]:
        """Get historical states for an endpoint."""
        pass
    
    @abstractmethod
    async def set_target_state(self, pool_id: str, state_id: str) -> bool:
        """Set a state as the target for a pool."""
        pass


class IRepositoryAnalyzer(ABC):
    """Interface for analyzing repository compatibility."""
    
    @abstractmethod
    async def analyze_pool_compatibility(self, pool_id: str) -> CompatibilityAnalysis:
        """Analyze package compatibility across pool endpoints."""
        pass
    
    @abstractmethod
    async def update_repository_info(self, endpoint_id: str, repositories: List[Repository]) -> bool:
        """Update repository information for an endpoint."""
        pass
    
    @abstractmethod
    async def get_repository_info(self, endpoint_id: str) -> List[Repository]:
        """Get repository information for an endpoint."""
        pass


class IPackmanInterface(ABC):
    """Interface for interacting with pacman."""
    
    @abstractmethod
    async def get_installed_packages(self) -> List[Dict[str, Any]]:
        """Get list of installed packages."""
        pass
    
    @abstractmethod
    async def get_repository_info(self) -> List[Dict[str, Any]]:
        """Get repository configuration and package lists."""
        pass
    
    @abstractmethod
    async def install_packages(self, packages: List[str]) -> bool:
        """Install specified packages."""
        pass
    
    @abstractmethod
    async def remove_packages(self, packages: List[str]) -> bool:
        """Remove specified packages."""
        pass
    
    @abstractmethod
    async def update_packages(self, packages: List[str]) -> bool:
        """Update specified packages."""
        pass
    
    @abstractmethod
    async def sync_repositories(self) -> bool:
        """Sync package repositories."""
        pass


class IAPIClient(ABC):
    """Interface for API client communication."""
    
    @abstractmethod
    async def authenticate(self, endpoint_name: str, hostname: str) -> str:
        """Authenticate and get access token."""
        pass
    
    @abstractmethod
    async def register_endpoint(self, name: str, hostname: str) -> Dict[str, Any]:
        """Register endpoint with server."""
        pass
    
    @abstractmethod
    async def report_status(self, endpoint_id: str, status: SyncStatus) -> bool:
        """Report endpoint status to server."""
        pass
    
    @abstractmethod
    async def submit_state(self, endpoint_id: str, state: SystemState) -> str:
        """Submit system state to server."""
        pass
    
    @abstractmethod
    async def get_target_state(self, pool_id: str) -> Optional[SystemState]:
        """Get target state for pool."""
        pass
    
    @abstractmethod
    async def trigger_sync(self, endpoint_id: str, operation: OperationType) -> str:
        """Trigger sync operation."""
        pass


class INotificationService(ABC):
    """Interface for desktop notifications."""
    
    @abstractmethod
    async def show_notification(self, title: str, message: str, icon: str = "info") -> None:
        """Show desktop notification."""
        pass
    
    @abstractmethod
    async def update_tray_icon(self, status: SyncStatus) -> None:
        """Update system tray icon."""
        pass
    
    @abstractmethod
    async def update_tray_tooltip(self, message: str) -> None:
        """Update system tray tooltip."""
        pass


class IConfigurationManager(ABC):
    """Interface for configuration management."""
    
    @abstractmethod
    def get_server_url(self) -> str:
        """Get server URL."""
        pass
    
    @abstractmethod
    def get_api_key(self) -> Optional[str]:
        """Get API key."""
        pass
    
    @abstractmethod
    def get_endpoint_name(self) -> str:
        """Get endpoint name."""
        pass
    
    @abstractmethod
    def get_pool_id(self) -> Optional[str]:
        """Get assigned pool ID."""
        pass
    
    @abstractmethod
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        pass
    
    @abstractmethod
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        pass