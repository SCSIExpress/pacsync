"""
Core data models for the Pacman Sync Utility.

This module defines the data structures used across the client-server architecture
for package states, pools, endpoints, and synchronization operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


class SyncStatus(Enum):
    """Endpoint synchronization status."""
    IN_SYNC = "in_sync"
    AHEAD = "ahead"
    BEHIND = "behind"
    OFFLINE = "offline"


class OperationType(Enum):
    """Types of synchronization operations."""
    SYNC = "sync"
    SET_LATEST = "set_latest"
    REVERT = "revert"


class OperationStatus(Enum):
    """Status of synchronization operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ConflictResolution(Enum):
    """Package conflict resolution strategies."""
    MANUAL = "manual"
    NEWEST = "newest"
    OLDEST = "oldest"


@dataclass
class PackageState:
    """Represents the state of a single package."""
    package_name: str
    version: str
    repository: str
    installed_size: int
    dependencies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.package_name:
            raise ValueError("Package name cannot be empty")
        if not self.version:
            raise ValueError("Package version cannot be empty")


@dataclass
class SystemState:
    """Represents the complete package state of an endpoint."""
    endpoint_id: str
    timestamp: datetime
    packages: List[PackageState]
    pacman_version: str
    architecture: str
    
    def __post_init__(self):
        if not self.endpoint_id:
            raise ValueError("Endpoint ID cannot be empty")
        if not self.packages:
            self.packages = []


@dataclass
class SyncPolicy:
    """Configuration for synchronization behavior."""
    auto_sync: bool = False
    exclude_packages: List[str] = field(default_factory=list)
    include_aur: bool = False
    conflict_resolution: ConflictResolution = ConflictResolution.MANUAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "auto_sync": self.auto_sync,
            "exclude_packages": self.exclude_packages,
            "include_aur": self.include_aur,
            "conflict_resolution": self.conflict_resolution.value
        }


@dataclass
class PackagePool:
    """Represents a group of endpoints that share package synchronization."""
    id: str
    name: str
    description: str
    endpoints: List[str] = field(default_factory=list)  # endpoint IDs
    target_state_id: Optional[str] = None
    sync_policy: SyncPolicy = field(default_factory=SyncPolicy)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.name:
            raise ValueError("Pool name cannot be empty")


@dataclass
class Endpoint:
    """Represents a client endpoint in the system."""
    id: str
    name: str
    hostname: str
    pool_id: Optional[str] = None
    last_seen: Optional[datetime] = None
    sync_status: SyncStatus = SyncStatus.OFFLINE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.name:
            raise ValueError("Endpoint name cannot be empty")
        if not self.hostname:
            raise ValueError("Endpoint hostname cannot be empty")


@dataclass
class RepositoryPackage:
    """Represents a package available in a repository."""
    name: str
    version: str
    repository: str
    architecture: str
    description: Optional[str] = None
    
    def __post_init__(self):
        if not self.name:
            raise ValueError("Package name cannot be empty")
        if not self.version:
            raise ValueError("Package version cannot be empty")


@dataclass
class PackageConflict:
    """Represents a conflict between package versions."""
    package_name: str
    endpoint_versions: Dict[str, str]  # endpoint_id -> version
    suggested_resolution: str
    
    def __post_init__(self):
        if not self.package_name:
            raise ValueError("Package name cannot be empty")
        if len(self.endpoint_versions) < 2:
            raise ValueError("Conflict must involve at least 2 endpoints")


@dataclass
class CompatibilityAnalysis:
    """Results of repository compatibility analysis for a pool."""
    pool_id: str
    common_packages: List[RepositoryPackage]
    excluded_packages: List[RepositoryPackage]
    conflicts: List[PackageConflict]
    last_analyzed: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.pool_id:
            raise ValueError("Pool ID cannot be empty")
        if not self.common_packages:
            self.common_packages = []
        if not self.excluded_packages:
            self.excluded_packages = []
        if not self.conflicts:
            self.conflicts = []


@dataclass
class SyncOperation:
    """Represents a synchronization operation."""
    id: str
    pool_id: str
    endpoint_id: str
    operation_type: OperationType
    status: OperationStatus = OperationStatus.PENDING
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.pool_id:
            raise ValueError("Pool ID cannot be empty")
        if not self.endpoint_id:
            raise ValueError("Endpoint ID cannot be empty")


@dataclass
class Repository:
    """Represents repository information from an endpoint."""
    id: str
    endpoint_id: str
    repo_name: str
    repo_url: Optional[str] = None
    packages: List[RepositoryPackage] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.endpoint_id:
            raise ValueError("Endpoint ID cannot be empty")
        if not self.repo_name:
            raise ValueError("Repository name cannot be empty")