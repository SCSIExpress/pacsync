#!/usr/bin/env python3
"""
Unit tests for core data models.

Tests all data model classes, validation logic, and business rules
to ensure data integrity and proper error handling.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from shared.models import (
    PackageState, SystemState, SyncPolicy, PackagePool, Endpoint,
    RepositoryPackage, PackageConflict, CompatibilityAnalysis,
    SyncOperation, Repository, SyncStatus, OperationType, 
    OperationStatus, ConflictResolution
)


class TestPackageState:
    """Test PackageState data model."""
    
    def test_valid_package_state_creation(self):
        """Test creating a valid PackageState."""
        package = PackageState(
            package_name="test-package",
            version="1.0.0",
            repository="core",
            installed_size=1024,
            dependencies=["dep1", "dep2"]
        )
        
        assert package.package_name == "test-package"
        assert package.version == "1.0.0"
        assert package.repository == "core"
        assert package.installed_size == 1024
        assert package.dependencies == ["dep1", "dep2"]
    
    def test_package_state_empty_dependencies(self):
        """Test PackageState with empty dependencies list."""
        package = PackageState(
            package_name="test-package",
            version="1.0.0",
            repository="core",
            installed_size=1024
        )
        
        assert package.dependencies == []
    
    def test_package_state_empty_name_validation(self):
        """Test that empty package name raises ValueError."""
        with pytest.raises(ValueError, match="Package name cannot be empty"):
            PackageState(
                package_name="",
                version="1.0.0",
                repository="core",
                installed_size=1024
            )
    
    def test_package_state_empty_version_validation(self):
        """Test that empty version raises ValueError."""
        with pytest.raises(ValueError, match="Package version cannot be empty"):
            PackageState(
                package_name="test-package",
                version="",
                repository="core",
                installed_size=1024
            )


class TestSystemState:
    """Test SystemState data model."""
    
    def test_valid_system_state_creation(self):
        """Test creating a valid SystemState."""
        packages = [
            PackageState("pkg1", "1.0.0", "core", 1024),
            PackageState("pkg2", "2.0.0", "extra", 2048)
        ]
        
        timestamp = datetime.now()
        state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=timestamp,
            packages=packages,
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        assert state.endpoint_id == "endpoint-1"
        assert state.timestamp == timestamp
        assert len(state.packages) == 2
        assert state.pacman_version == "6.0.1"
        assert state.architecture == "x86_64"
    
    def test_system_state_empty_packages(self):
        """Test SystemState with empty packages list."""
        state = SystemState(
            endpoint_id="endpoint-1",
            timestamp=datetime.now(),
            packages=[],
            pacman_version="6.0.1",
            architecture="x86_64"
        )
        
        assert state.packages == []
    
    def test_system_state_empty_endpoint_validation(self):
        """Test that empty endpoint ID raises ValueError."""
        with pytest.raises(ValueError, match="Endpoint ID cannot be empty"):
            SystemState(
                endpoint_id="",
                timestamp=datetime.now(),
                packages=[],
                pacman_version="6.0.1",
                architecture="x86_64"
            )


class TestSyncPolicy:
    """Test SyncPolicy data model."""
    
    def test_default_sync_policy(self):
        """Test default SyncPolicy values."""
        policy = SyncPolicy()
        
        assert policy.auto_sync == False
        assert policy.exclude_packages == []
        assert policy.include_aur == False
        assert policy.conflict_resolution == ConflictResolution.MANUAL
    
    def test_custom_sync_policy(self):
        """Test custom SyncPolicy values."""
        policy = SyncPolicy(
            auto_sync=True,
            exclude_packages=["pkg1", "pkg2"],
            include_aur=True,
            conflict_resolution=ConflictResolution.NEWEST
        )
        
        assert policy.auto_sync == True
        assert policy.exclude_packages == ["pkg1", "pkg2"]
        assert policy.include_aur == True
        assert policy.conflict_resolution == ConflictResolution.NEWEST
    
    def test_sync_policy_to_dict(self):
        """Test SyncPolicy to_dict conversion."""
        policy = SyncPolicy(
            auto_sync=True,
            exclude_packages=["pkg1"],
            include_aur=False,
            conflict_resolution=ConflictResolution.OLDEST
        )
        
        result = policy.to_dict()
        expected = {
            "auto_sync": True,
            "exclude_packages": ["pkg1"],
            "include_aur": False,
            "conflict_resolution": "oldest"
        }
        
        assert result == expected


class TestPackagePool:
    """Test PackagePool data model."""
    
    def test_valid_package_pool_creation(self):
        """Test creating a valid PackagePool."""
        pool = PackagePool(
            id="pool-1",
            name="Test Pool",
            description="A test pool",
            endpoints=["endpoint-1", "endpoint-2"]
        )
        
        assert pool.id == "pool-1"
        assert pool.name == "Test Pool"
        assert pool.description == "A test pool"
        assert pool.endpoints == ["endpoint-1", "endpoint-2"]
        assert isinstance(pool.sync_policy, SyncPolicy)
        assert isinstance(pool.created_at, datetime)
        assert isinstance(pool.updated_at, datetime)
    
    def test_package_pool_auto_id_generation(self):
        """Test that PackagePool generates ID if not provided."""
        pool = PackagePool(
            id="",
            name="Test Pool",
            description="A test pool"
        )
        
        assert pool.id != ""
        assert len(pool.id) == 36  # UUID4 length
    
    def test_package_pool_empty_name_validation(self):
        """Test that empty pool name raises ValueError."""
        with pytest.raises(ValueError, match="Pool name cannot be empty"):
            PackagePool(
                id="pool-1",
                name="",
                description="A test pool"
            )
    
    def test_package_pool_default_values(self):
        """Test PackagePool default values."""
        pool = PackagePool(
            id="pool-1",
            name="Test Pool",
            description="A test pool"
        )
        
        assert pool.endpoints == []
        assert pool.target_state_id is None
        assert isinstance(pool.sync_policy, SyncPolicy)


class TestEndpoint:
    """Test Endpoint data model."""
    
    def test_valid_endpoint_creation(self):
        """Test creating a valid Endpoint."""
        endpoint = Endpoint(
            id="endpoint-1",
            name="Test Endpoint",
            hostname="test-host",
            pool_id="pool-1",
            sync_status=SyncStatus.IN_SYNC
        )
        
        assert endpoint.id == "endpoint-1"
        assert endpoint.name == "Test Endpoint"
        assert endpoint.hostname == "test-host"
        assert endpoint.pool_id == "pool-1"
        assert endpoint.sync_status == SyncStatus.IN_SYNC
        assert isinstance(endpoint.created_at, datetime)
        assert isinstance(endpoint.updated_at, datetime)
    
    def test_endpoint_auto_id_generation(self):
        """Test that Endpoint generates ID if not provided."""
        endpoint = Endpoint(
            id="",
            name="Test Endpoint",
            hostname="test-host"
        )
        
        assert endpoint.id != ""
        assert len(endpoint.id) == 36  # UUID4 length
    
    def test_endpoint_empty_name_validation(self):
        """Test that empty endpoint name raises ValueError."""
        with pytest.raises(ValueError, match="Endpoint name cannot be empty"):
            Endpoint(
                id="endpoint-1",
                name="",
                hostname="test-host"
            )
    
    def test_endpoint_empty_hostname_validation(self):
        """Test that empty hostname raises ValueError."""
        with pytest.raises(ValueError, match="Endpoint hostname cannot be empty"):
            Endpoint(
                id="endpoint-1",
                name="Test Endpoint",
                hostname=""
            )
    
    def test_endpoint_default_values(self):
        """Test Endpoint default values."""
        endpoint = Endpoint(
            id="endpoint-1",
            name="Test Endpoint",
            hostname="test-host"
        )
        
        assert endpoint.pool_id is None
        assert endpoint.last_seen is None
        assert endpoint.sync_status == SyncStatus.OFFLINE


class TestRepositoryPackage:
    """Test RepositoryPackage data model."""
    
    def test_valid_repository_package_creation(self):
        """Test creating a valid RepositoryPackage."""
        package = RepositoryPackage(
            name="test-package",
            version="1.0.0",
            repository="core",
            architecture="x86_64",
            description="Test package"
        )
        
        assert package.name == "test-package"
        assert package.version == "1.0.0"
        assert package.repository == "core"
        assert package.architecture == "x86_64"
        assert package.description == "Test package"
    
    def test_repository_package_empty_name_validation(self):
        """Test that empty package name raises ValueError."""
        with pytest.raises(ValueError, match="Package name cannot be empty"):
            RepositoryPackage(
                name="",
                version="1.0.0",
                repository="core",
                architecture="x86_64"
            )
    
    def test_repository_package_empty_version_validation(self):
        """Test that empty version raises ValueError."""
        with pytest.raises(ValueError, match="Package version cannot be empty"):
            RepositoryPackage(
                name="test-package",
                version="",
                repository="core",
                architecture="x86_64"
            )


class TestPackageConflict:
    """Test PackageConflict data model."""
    
    def test_valid_package_conflict_creation(self):
        """Test creating a valid PackageConflict."""
        conflict = PackageConflict(
            package_name="test-package",
            endpoint_versions={"endpoint-1": "1.0.0", "endpoint-2": "2.0.0"},
            suggested_resolution="Use version 2.0.0"
        )
        
        assert conflict.package_name == "test-package"
        assert conflict.endpoint_versions == {"endpoint-1": "1.0.0", "endpoint-2": "2.0.0"}
        assert conflict.suggested_resolution == "Use version 2.0.0"
    
    def test_package_conflict_empty_name_validation(self):
        """Test that empty package name raises ValueError."""
        with pytest.raises(ValueError, match="Package name cannot be empty"):
            PackageConflict(
                package_name="",
                endpoint_versions={"endpoint-1": "1.0.0", "endpoint-2": "2.0.0"},
                suggested_resolution="Use version 2.0.0"
            )
    
    def test_package_conflict_insufficient_endpoints_validation(self):
        """Test that conflict with less than 2 endpoints raises ValueError."""
        with pytest.raises(ValueError, match="Conflict must involve at least 2 endpoints"):
            PackageConflict(
                package_name="test-package",
                endpoint_versions={"endpoint-1": "1.0.0"},
                suggested_resolution="Use version 1.0.0"
            )


class TestCompatibilityAnalysis:
    """Test CompatibilityAnalysis data model."""
    
    def test_valid_compatibility_analysis_creation(self):
        """Test creating a valid CompatibilityAnalysis."""
        common_packages = [
            RepositoryPackage("pkg1", "1.0.0", "core", "x86_64")
        ]
        excluded_packages = [
            RepositoryPackage("pkg2", "2.0.0", "extra", "x86_64")
        ]
        conflicts = [
            PackageConflict("pkg3", {"endpoint-1": "1.0.0", "endpoint-2": "2.0.0"}, "Use 2.0.0")
        ]
        
        analysis = CompatibilityAnalysis(
            pool_id="pool-1",
            common_packages=common_packages,
            excluded_packages=excluded_packages,
            conflicts=conflicts
        )
        
        assert analysis.pool_id == "pool-1"
        assert len(analysis.common_packages) == 1
        assert len(analysis.excluded_packages) == 1
        assert len(analysis.conflicts) == 1
        assert isinstance(analysis.last_analyzed, datetime)
    
    def test_compatibility_analysis_empty_pool_validation(self):
        """Test that empty pool ID raises ValueError."""
        with pytest.raises(ValueError, match="Pool ID cannot be empty"):
            CompatibilityAnalysis(
                pool_id="",
                common_packages=[],
                excluded_packages=[],
                conflicts=[]
            )
    
    def test_compatibility_analysis_default_values(self):
        """Test CompatibilityAnalysis default values."""
        analysis = CompatibilityAnalysis(
            pool_id="pool-1",
            common_packages=[],
            excluded_packages=[],
            conflicts=[]
        )
        
        assert analysis.common_packages == []
        assert analysis.excluded_packages == []
        assert analysis.conflicts == []


class TestSyncOperation:
    """Test SyncOperation data model."""
    
    def test_valid_sync_operation_creation(self):
        """Test creating a valid SyncOperation."""
        operation = SyncOperation(
            id="op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SYNC,
            status=OperationStatus.PENDING,
            details={"test": "data"}
        )
        
        assert operation.id == "op-1"
        assert operation.pool_id == "pool-1"
        assert operation.endpoint_id == "endpoint-1"
        assert operation.operation_type == OperationType.SYNC
        assert operation.status == OperationStatus.PENDING
        assert operation.details == {"test": "data"}
        assert isinstance(operation.created_at, datetime)
        assert operation.completed_at is None
        assert operation.error_message is None
    
    def test_sync_operation_auto_id_generation(self):
        """Test that SyncOperation generates ID if not provided."""
        operation = SyncOperation(
            id="",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SYNC
        )
        
        assert operation.id != ""
        assert len(operation.id) == 36  # UUID4 length
    
    def test_sync_operation_empty_pool_validation(self):
        """Test that empty pool ID raises ValueError."""
        with pytest.raises(ValueError, match="Pool ID cannot be empty"):
            SyncOperation(
                id="op-1",
                pool_id="",
                endpoint_id="endpoint-1",
                operation_type=OperationType.SYNC
            )
    
    def test_sync_operation_empty_endpoint_validation(self):
        """Test that empty endpoint ID raises ValueError."""
        with pytest.raises(ValueError, match="Endpoint ID cannot be empty"):
            SyncOperation(
                id="op-1",
                pool_id="pool-1",
                endpoint_id="",
                operation_type=OperationType.SYNC
            )
    
    def test_sync_operation_default_values(self):
        """Test SyncOperation default values."""
        operation = SyncOperation(
            id="op-1",
            pool_id="pool-1",
            endpoint_id="endpoint-1",
            operation_type=OperationType.SYNC
        )
        
        assert operation.status == OperationStatus.PENDING
        assert operation.details == {}


class TestRepository:
    """Test Repository data model."""
    
    def test_valid_repository_creation(self):
        """Test creating a valid Repository."""
        packages = [
            RepositoryPackage("pkg1", "1.0.0", "core", "x86_64")
        ]
        
        repository = Repository(
            id="repo-1",
            endpoint_id="endpoint-1",
            repo_name="core",
            repo_url="https://mirror.example.com/core",
            packages=packages
        )
        
        assert repository.id == "repo-1"
        assert repository.endpoint_id == "endpoint-1"
        assert repository.repo_name == "core"
        assert repository.repo_url == "https://mirror.example.com/core"
        assert len(repository.packages) == 1
        assert isinstance(repository.last_updated, datetime)
    
    def test_repository_auto_id_generation(self):
        """Test that Repository generates ID if not provided."""
        repository = Repository(
            id="",
            endpoint_id="endpoint-1",
            repo_name="core"
        )
        
        assert repository.id != ""
        assert len(repository.id) == 36  # UUID4 length
    
    def test_repository_empty_endpoint_validation(self):
        """Test that empty endpoint ID raises ValueError."""
        with pytest.raises(ValueError, match="Endpoint ID cannot be empty"):
            Repository(
                id="repo-1",
                endpoint_id="",
                repo_name="core"
            )
    
    def test_repository_empty_name_validation(self):
        """Test that empty repository name raises ValueError."""
        with pytest.raises(ValueError, match="Repository name cannot be empty"):
            Repository(
                id="repo-1",
                endpoint_id="endpoint-1",
                repo_name=""
            )
    
    def test_repository_default_values(self):
        """Test Repository default values."""
        repository = Repository(
            id="repo-1",
            endpoint_id="endpoint-1",
            repo_name="core"
        )
        
        assert repository.repo_url is None
        assert repository.packages == []


class TestEnums:
    """Test enumeration classes."""
    
    def test_sync_status_enum(self):
        """Test SyncStatus enum values."""
        assert SyncStatus.IN_SYNC.value == "in_sync"
        assert SyncStatus.AHEAD.value == "ahead"
        assert SyncStatus.BEHIND.value == "behind"
        assert SyncStatus.OFFLINE.value == "offline"
    
    def test_operation_type_enum(self):
        """Test OperationType enum values."""
        assert OperationType.SYNC.value == "sync"
        assert OperationType.SET_LATEST.value == "set_latest"
        assert OperationType.REVERT.value == "revert"
    
    def test_operation_status_enum(self):
        """Test OperationStatus enum values."""
        assert OperationStatus.PENDING.value == "pending"
        assert OperationStatus.IN_PROGRESS.value == "in_progress"
        assert OperationStatus.COMPLETED.value == "completed"
        assert OperationStatus.FAILED.value == "failed"
    
    def test_conflict_resolution_enum(self):
        """Test ConflictResolution enum values."""
        assert ConflictResolution.MANUAL.value == "manual"
        assert ConflictResolution.NEWEST.value == "newest"
        assert ConflictResolution.OLDEST.value == "oldest"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])