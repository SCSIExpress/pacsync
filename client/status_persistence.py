"""
Status Persistence for Pacman Sync Utility Client.

This module handles persistent storage of sync status and state information
to maintain consistency between GUI and CLI modes.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Import SyncStatus with fallback
try:
    from client.qt.application import SyncStatus
except ImportError:
    # Define SyncStatus locally if Qt is not available
    from enum import Enum
    class SyncStatus(Enum):
        IN_SYNC = "in_sync"
        AHEAD = "ahead"
        BEHIND = "behind"
        OFFLINE = "offline"
        SYNCING = "syncing"
        ERROR = "error"

logger = logging.getLogger(__name__)


@dataclass
class PersistedStatus:
    """Persistent status information."""
    status: SyncStatus
    last_updated: datetime
    endpoint_id: Optional[str] = None
    endpoint_name: Optional[str] = None
    pool_id: Optional[str] = None
    last_sync_time: Optional[datetime] = None
    last_operation: Optional[str] = None
    operation_result: Optional[str] = None
    packages_count: Optional[int] = None
    server_url: Optional[str] = None
    is_authenticated: bool = False


class StatusPersistenceManager:
    """
    Manages persistent storage of sync status and related information.
    
    Provides a way to maintain status consistency between GUI and CLI modes
    by storing status information in a local file.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the status persistence manager.
        
        Args:
            config_dir: Optional custom configuration directory
        """
        self._config_dir = self._get_config_directory(config_dir)
        self._status_file = self._config_dir / "status.json"
        self._lock_file = self._config_dir / "status.lock"
        
        # Ensure config directory exists
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Status persistence initialized: {self._status_file}")
    
    def _get_config_directory(self, custom_dir: Optional[str] = None) -> Path:
        """Get the configuration directory path."""
        if custom_dir:
            return Path(custom_dir)
        
        # Use XDG config directory if available
        xdg_config = os.environ.get('XDG_CONFIG_HOME')
        if xdg_config:
            return Path(xdg_config) / 'pacman-sync'
        else:
            return Path.home() / '.config' / 'pacman-sync'
    
    def _acquire_lock(self, timeout: float = 5.0) -> bool:
        """
        Acquire a file lock to prevent concurrent access.
        
        Args:
            timeout: Maximum time to wait for lock acquisition
            
        Returns:
            True if lock was acquired, False otherwise
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to create lock file exclusively
                with open(self._lock_file, 'x') as f:
                    f.write(str(os.getpid()))
                return True
            except FileExistsError:
                # Lock file exists, check if process is still running
                try:
                    with open(self._lock_file, 'r') as f:
                        pid = int(f.read().strip())
                    
                    # Check if process is still running (Unix-specific)
                    try:
                        os.kill(pid, 0)  # Signal 0 just checks if process exists
                        # Process is running, wait a bit
                        time.sleep(0.1)
                        continue
                    except (OSError, ProcessLookupError):
                        # Process is not running, remove stale lock
                        self._lock_file.unlink(missing_ok=True)
                        continue
                        
                except (ValueError, FileNotFoundError):
                    # Invalid lock file, remove it
                    self._lock_file.unlink(missing_ok=True)
                    continue
            except Exception as e:
                logger.warning(f"Failed to acquire lock: {e}")
                return False
        
        logger.warning(f"Failed to acquire lock within {timeout} seconds")
        return False
    
    def _release_lock(self) -> None:
        """Release the file lock."""
        try:
            self._lock_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to release lock: {e}")
    
    def save_status(self, status: PersistedStatus) -> bool:
        """
        Save status information to persistent storage.
        
        Args:
            status: Status information to save
            
        Returns:
            True if successful, False otherwise
        """
        if not self._acquire_lock():
            logger.error("Failed to acquire lock for status save")
            return False
        
        try:
            # Convert to dictionary for JSON serialization
            status_dict = asdict(status)
            
            # Convert datetime objects to ISO format strings
            for key, value in status_dict.items():
                if isinstance(value, datetime):
                    status_dict[key] = value.isoformat()
                elif isinstance(value, SyncStatus):
                    status_dict[key] = value.value
            
            # Write to temporary file first, then rename for atomic operation
            temp_file = self._status_file.with_suffix('.tmp')
            
            with open(temp_file, 'w') as f:
                json.dump(status_dict, f, indent=2)
            
            # Atomic rename
            temp_file.replace(self._status_file)
            
            logger.debug(f"Status saved: {status.status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save status: {e}")
            return False
        finally:
            self._release_lock()
    
    def load_status(self) -> Optional[PersistedStatus]:
        """
        Load status information from persistent storage.
        
        Returns:
            Loaded status information or None if not available
        """
        if not self._status_file.exists():
            logger.debug("Status file does not exist")
            return None
        
        if not self._acquire_lock():
            logger.error("Failed to acquire lock for status load")
            return None
        
        try:
            with open(self._status_file, 'r') as f:
                status_dict = json.load(f)
            
            # Convert string values back to appropriate types
            if 'status' in status_dict:
                status_dict['status'] = SyncStatus(status_dict['status'])
            
            for key in ['last_updated', 'last_sync_time']:
                if key in status_dict and status_dict[key]:
                    status_dict[key] = datetime.fromisoformat(status_dict[key])
            
            # Create PersistedStatus object
            status = PersistedStatus(**status_dict)
            
            logger.debug(f"Status loaded: {status.status.value}")
            return status
            
        except Exception as e:
            logger.error(f"Failed to load status: {e}")
            return None
        finally:
            self._release_lock()
    
    def update_status(self, status: SyncStatus, **kwargs) -> bool:
        """
        Update only the status field, preserving other information.
        
        Args:
            status: New sync status
            **kwargs: Additional fields to update
            
        Returns:
            True if successful, False otherwise
        """
        # Load existing status or create new one
        current = self.load_status()
        if current is None:
            current = PersistedStatus(
                status=status,
                last_updated=datetime.now()
            )
        else:
            current.status = status
            current.last_updated = datetime.now()
        
        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(current, key):
                setattr(current, key, value)
        
        return self.save_status(current)
    
    def update_operation_result(self, operation: str, success: bool, message: str) -> bool:
        """
        Update the last operation result.
        
        Args:
            operation: Operation type (sync, set_latest, revert)
            success: Whether the operation was successful
            message: Result message
            
        Returns:
            True if successful, False otherwise
        """
        current = self.load_status()
        if current is None:
            current = PersistedStatus(
                status=SyncStatus.OFFLINE,
                last_updated=datetime.now()
            )
        
        current.last_operation = operation
        current.operation_result = f"{'SUCCESS' if success else 'FAILED'}: {message}"
        current.last_updated = datetime.now()
        
        if operation in ['sync', 'set_latest', 'revert']:
            current.last_sync_time = datetime.now()
        
        return self.save_status(current)
    
    def update_authentication(self, is_authenticated: bool, endpoint_id: Optional[str] = None,
                            endpoint_name: Optional[str] = None, server_url: Optional[str] = None) -> bool:
        """
        Update authentication status.
        
        Args:
            is_authenticated: Whether client is authenticated
            endpoint_id: Endpoint ID if authenticated
            endpoint_name: Endpoint name if authenticated
            server_url: Server URL
            
        Returns:
            True if successful, False otherwise
        """
        current = self.load_status()
        if current is None:
            current = PersistedStatus(
                status=SyncStatus.OFFLINE if not is_authenticated else SyncStatus.IN_SYNC,
                last_updated=datetime.now()
            )
        
        current.is_authenticated = is_authenticated
        current.endpoint_id = endpoint_id
        current.endpoint_name = endpoint_name
        current.server_url = server_url
        current.last_updated = datetime.now()
        
        # Update status based on authentication
        if not is_authenticated:
            current.status = SyncStatus.OFFLINE
        elif current.status == SyncStatus.OFFLINE:
            current.status = SyncStatus.IN_SYNC  # Default to in_sync when connected
        
        return self.save_status(current)
    
    def is_status_fresh(self, max_age_seconds: int = 300) -> bool:
        """
        Check if the persisted status is fresh (recently updated).
        
        Args:
            max_age_seconds: Maximum age in seconds to consider fresh
            
        Returns:
            True if status is fresh, False otherwise
        """
        status = self.load_status()
        if status is None:
            return False
        
        age = datetime.now() - status.last_updated
        return age.total_seconds() <= max_age_seconds
    
    def clear_status(self) -> bool:
        """
        Clear the persisted status file.
        
        Returns:
            True if successful, False otherwise
        """
        if not self._acquire_lock():
            logger.error("Failed to acquire lock for status clear")
            return False
        
        try:
            self._status_file.unlink(missing_ok=True)
            logger.info("Status file cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear status: {e}")
            return False
        finally:
            self._release_lock()
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current status for display purposes.
        
        Returns:
            Dictionary containing status summary
        """
        status = self.load_status()
        if status is None:
            return {
                'status': 'unknown',
                'message': 'No status information available',
                'last_updated': None
            }
        
        # Calculate time since last update
        age = datetime.now() - status.last_updated
        if age.total_seconds() < 60:
            age_str = f"{int(age.total_seconds())} seconds ago"
        elif age.total_seconds() < 3600:
            age_str = f"{int(age.total_seconds() / 60)} minutes ago"
        else:
            age_str = f"{int(age.total_seconds() / 3600)} hours ago"
        
        return {
            'status': status.status.value,
            'endpoint_name': status.endpoint_name or 'Unknown',
            'server_url': status.server_url or 'Unknown',
            'is_authenticated': status.is_authenticated,
            'last_updated': age_str,
            'last_operation': status.last_operation,
            'operation_result': status.operation_result,
            'packages_count': status.packages_count,
            'last_sync_time': status.last_sync_time.strftime('%Y-%m-%d %H:%M:%S') if status.last_sync_time else None
        }