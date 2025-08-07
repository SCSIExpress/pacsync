#!/usr/bin/env python3
"""
Unit tests for RepositoryAnalyzer core service.

Tests repository analysis functionality including compatibility analysis,
package exclusion management, and repository information processing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from server.core.repository_analyzer import (
    RepositoryAnalyzer, PackageAvailability
)
from shared.models import (
    CompatibilityAnalysis, Repository, RepositoryPackage, PackageConflict,
    PackagePool, Endpoint, SyncPolicy, ConflictResolution
)


class TestPackageAvailability:
    """Test PackageAvailability helper class."""
    
    def test_package_availability_creation(self):
        """Test creating PackageAvailability."""
        availability = PackageAvailability("test-package")
        
        assert availability.package_name == "test-package"
        assert availability.endpoint_versions == {}
        assert availability.endpoint_repositories == {}
        assert availability.endpoint_architectures == {}
    
    def test_add_endpoint_package(self):
        """Test adding endpoint package information."""
        availability = PackageAvailability("test-package")
        package = RepositoryPackage(
            name="test-package",
            version="1.0.0",
            repository="core",
            architecture="x86_64"
        )
        
        availability.add_endpoint_package("endpoint-1", package)
        
        assert availability.endpoint_versions["endpoint-1"] == "1.0.0"
        assert availability.endpoint_repositories["endpoint-1"] == "core"
        assert availability.endpoint_architectures["endpoint-1"] == "x86_64"
    
    def test_available_endpoints_property(self):
        """Test available_endpoints property."""
        availability = PackageAvailability("test-package")
        
        package1 = RepositoryPackage("test-package", "1.0.0", "core", "x86_64")
        package2 = RepositoryPackage("test-package", "1.0.0", "core", "x86_64")
        
        availability.add_endpoint_package("endpoint-1", package1)
        availability.add_endpoint_package("endpoint-2", package2)
        
        assert availability.available_endpoints == {"endpoint-1", "endpoint-2"}
    
    def test_unique_versions_property(self):
        """Test unique_versions property."""
        availability = PackageAvailability("test-package")
        
        package1 = RepositoryPackage("test-package", "1.0.0", "core", "x86_64")
        package2 = RepositoryPackage("test-package", "2.0.0", "core", "x86_64")
        package3 = RepositoryPackage("test-package", "1.0.0", "core", "x86_64")
        
        availability.add_endpoint_package("endpoint-1", package1)
        availability.add_endpoint_package("endpoint-2", package2)
        availability.add_endpoint_package("endpoint-3", package3)
        
        assert availability.unique_versions == {"1.0.0", "2.0.0"}
    
    def test_has_version_conflicts_property(self):
        """Test has_version_conflicts property."""
        availability = PackageAvailability("test-package")
        
        # No conflicts - same version
        package1 = RepositoryPackage("test-package", "1.0.0", "core", "x86_64")
        package2 = RepositoryPackage("test-package", "1.0.0", "core", "x86_64")
        
        availability.add_endpoint_package("endpoint-1", package1)
        availability.add_endpoint_package("endpoint-2", package2)
        
        assert availability.has_version_conflicts == False
        
        # Has conflicts - different versions
        package3 = RepositoryPackage("test-package", "2.0.0", "core", "x86_64")
        availability.add_endpoint_package("endpoint-3", package3)
        
        assert availability.has_version_conflicts == True
    
    def test_get_most_common_version(self):
        """Test get_most_common_version method."""
        availability = PackageAvailability("test-package")
        
        # Add packages with different versions
        packages = [
            ("endpoint-1", "1.0.0"),
            ("endpoint-2", "2.0.0"),
            ("endpoint-3", "1.0.0"),
            ("endpoint-4", "1.0.0")
        ]
        
        for endpoint_id, version in packages:
            package = RepositoryPackage("test-package", version, "core", "x86_64")
            availability.add_endpoint_package(endpoint_id, package)
        
        # 1.0.0 appears 3 times, 2.0.0 appears 1 time
        assert availability.get_most_common_version() == "1.0.0"
    
    def test_create_conflict(self):
        """Test create_conflict method."""
        availability = PackageAvailability("test-package")
        
        package1 = RepositoryPackage("test-package", "1.0.0", "core", "x86_64")
        package2 = RepositoryPackage("test-package", "2.0.0", "core", "x86_64")
        
        availability.add_endpoint_package("endpoint-1", package1)
        availability.add_endpoint_package("endpoint-2", package2)
        
        conflict = availability.create_conflict()
        
        assert isinstance(conflict, PackageConflict)
        assert conflict.package_name == "test-package"
        assert conflict.endpoint_versions == {"endpoint-1": "1.0.0", "endpoint-2": "2.0.0"}
        assert "1.0.0" in conflict.suggested_resolution or "2.0.0" in conflict.suggested_resolution


class TestRepositoryAnalyzer:
    """Test RepositoryAnalyzer core service."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        return MagicMock()
    
    @pytest.fixture
    def mock_repo_repository(self):
        """Create mock repository repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_pool_repository(self):
        """Create mock pool repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_endpoint_repository(self):
        """Create mock endpoint repository."""
        return AsyncMock()
    
    @pytest.fixture
    def repository_analyzer(self, mock_db_manager, mock_repo_repository, 
                           mock_pool_repository, mock_endpoint_repository):
        """Create RepositoryAnalyzer with mocked dependencies."""
        analyzer = RepositoryAnalyzer(mock_db_manager)
        analyzer.repo_repository = mock_repo_repository
        analyzer.pool_repository = mock_pool_repository
        analyzer.endpoint_repository = mock_endpoint_repository
        return analyzer
    
    @pytest.mark.asyncio
    async def test_analyze_pool_compatibility_success(self, repository_analyzer, 
                                                     mock_pool_repository, mock_endpoint_repository,
                                                     mock_repo_repository):
        """Test successful pool compatibility analysis."""
        # Setup test data
        pool = PackagePool(
            id="pool-1",
            name="Test Pool",
            description="Test pool",
            sync_policy=SyncPolicy(exclude_packages=["excluded-pkg"])
        )
        
        endpoints = [
            Endpoint("endpoint-1", "Endpoint 1", "host1"),
            Endpoint("endpoint-2", "Endpoint 2", "host2")
        ]
        
        # Repository data for endpoint 1
        repo1_packages = [
            RepositoryPackage("common-pkg", "1.0.0", "core", "x86_64"),
            RepositoryPackage("conflict-pkg", "1.0.0", "core", "x86_64"),
            RepositoryPackage("missing-pkg", "1.0.0", "core", "x86_64"),
            RepositoryPackage("excluded-pkg", "1.0.0", "core", "x86_64")
        ]
        repo1 = Repository("repo-1", "endpoint-1", "core", packages=repo1_packages)
        
        # Repository data for endpoint 2
        repo2_packages = [
            RepositoryPackage("common-pkg", "1.0.0", "core", "x86_64"),
            RepositoryPackage("conflict-pkg", "2.0.0", "core", "x86_64"),
            RepositoryPackage("excluded-pkg", "1.0.0", "core", "x86_64")
        ]
        repo2 = Repository("repo-2", "endpoint-2", "core", packages=repo2_packages)
        
        # Setup mocks
        mock_pool_repository.get_by_id.return_value = pool
        mock_endpoint_repository.list_by_pool.return_value = endpoints
        mock_repo_repository.list_by_endpoint.side_effect = [
            [repo1], [repo2]
        ]
        
        # Execute
        result = await repository_analyzer.analyze_pool_compatibility("pool-1")
        
        # Verify
        assert isinstance(result, CompatibilityAnalysis)
        assert result.pool_id == "pool-1"
        
        # Check common packages (available on all endpoints with same version)
        common_names = [pkg.name for pkg in result.common_packages]
        assert "common-pkg" in common_names
        
        # Check excluded packages (missing from some endpoints or excluded by policy)
        excluded_names = [pkg.name for pkg in result.excluded_packages]
        assert "missing-pkg" in excluded_names  # Only on endpoint-1
        assert "excluded-pkg" in excluded_names  # Excluded by policy
        
        # Check conflicts (different versions across endpoints)
        conflict_names = [conflict.package_name for conflict in result.conflicts]
        assert "conflict-pkg" in conflict_names
    
    @pytest.mark.asyncio
    async def test_analyze_pool_compatibility_pool_not_found(self, repository_analyzer, 
                                                            mock_pool_repository):
        """Test pool compatibility analysis when pool doesn't exist."""
        mock_pool_repository.get_by_id.return_value = None
        
        result = await repository_analyzer.analyze_pool_compatibility("non-existent")
        
        assert isinstance(result, CompatibilityAnalysis)
        assert result.pool_id == "non-existent"
        assert result.common_packages == []
        assert result.excluded_packages == []
        assert result.conflicts == []
    
    @pytest.mark.asyncio
    async def test_analyze_pool_compatibility_no_endpoints(self, repository_analyzer, 
                                                          mock_pool_repository, mock_endpoint_repository):
        """Test pool compatibility analysis with no endpoints."""
        pool = PackagePool("pool-1", "Test Pool", "Test pool")
        mock_pool_repository.get_by_id.return_value = pool
        mock_endpoint_repository.list_by_pool.return_value = []
        
        result = await repository_analyzer.analyze_pool_compatibility("pool-1")
        
        assert isinstance(result, CompatibilityAnalysis)
        assert result.pool_id == "pool-1"
        assert result.common_packages == []
        assert result.excluded_packages == []
        assert result.conflicts == []
    
    @pytest.mark.asyncio
    async def test_update_repository_info_success(self, repository_analyzer, 
                                                 mock_endpoint_repository, mock_repo_repository):
        """Test successful repository information update."""
        endpoint = Endpoint("endpoint-1", "Test Endpoint", "host1", pool_id="pool-1")
        mock_endpoint_repository.get_by_id.return_value = endpoint
        mock_repo_repository.delete_by_endpoint.return_value = True
        mock_repo_repository.create_or_update.return_value = True
        
        repositories = [
            Repository("repo-1", "endpoint-1", "core", packages=[
                RepositoryPackage("pkg1", "1.0.0", "core", "x86_64")
            ]),
            Repository("repo-2", "endpoint-1", "extra", packages=[
                RepositoryPackage("pkg2", "2.0.0", "extra", "x86_64")
            ])
        ]
        
        # Mock the analyze_pool_compatibility method to avoid recursion
        with patch.object(repository_analyzer, 'analyze_pool_compatibility') as mock_analyze:
            result = await repository_analyzer.update_repository_info("endpoint-1", repositories)
        
        assert result == True
        mock_endpoint_repository.get_by_id.assert_called_once_with("endpoint-1")
        mock_repo_repository.delete_by_endpoint.assert_called_once_with("endpoint-1")
        assert mock_repo_repository.create_or_update.call_count == 2
        
        # Should trigger compatibility analysis since endpoint is in a pool
        mock_analyze.assert_called_once_with("pool-1")
    
    @pytest.mark.asyncio
    async def test_update_repository_info_endpoint_not_found(self, repository_analyzer, 
                                                            mock_endpoint_repository):
        """Test repository info update when endpoint doesn't exist."""
        mock_endpoint_repository.get_by_id.return_value = None
        
        result = await repository_analyzer.update_repository_info("non-existent", [])
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_update_repository_info_no_pool_trigger(self, repository_analyzer, 
                                                         mock_endpoint_repository, mock_repo_repository):
        """Test repository info update when endpoint has no pool (no analysis trigger)."""
        endpoint = Endpoint("endpoint-1", "Test Endpoint", "host1", pool_id=None)
        mock_endpoint_repository.get_by_id.return_value = endpoint
        mock_repo_repository.delete_by_endpoint.return_value = True
        mock_repo_repository.create_or_update.return_value = True
        
        repositories = [
            Repository("repo-1", "endpoint-1", "core", packages=[])
        ]
        
        with patch.object(repository_analyzer, 'analyze_pool_compatibility') as mock_analyze:
            result = await repository_analyzer.update_repository_info("endpoint-1", repositories)
        
        assert result == True
        # Should not trigger compatibility analysis since endpoint has no pool
        mock_analyze.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_repository_info_success(self, repository_analyzer, mock_repo_repository):
        """Test successful repository information retrieval."""
        expected_repositories = [
            Repository("repo-1", "endpoint-1", "core", packages=[]),
            Repository("repo-2", "endpoint-1", "extra", packages=[])
        ]
        mock_repo_repository.list_by_endpoint.return_value = expected_repositories
        
        result = await repository_analyzer.get_repository_info("endpoint-1")
        
        assert result == expected_repositories
        mock_repo_repository.list_by_endpoint.assert_called_once_with("endpoint-1")
    
    @pytest.mark.asyncio
    async def test_get_pool_package_matrix_success(self, repository_analyzer, 
                                                  mock_endpoint_repository, mock_repo_repository):
        """Test successful package matrix generation."""
        endpoints = [
            Endpoint("endpoint-1", "Endpoint 1", "host1"),
            Endpoint("endpoint-2", "Endpoint 2", "host2")
        ]
        
        # Repository data
        repo1_packages = [
            RepositoryPackage("pkg1", "1.0.0", "core", "x86_64"),
            RepositoryPackage("pkg2", "2.0.0", "core", "x86_64")
        ]
        repo1 = Repository("repo-1", "endpoint-1", "core", packages=repo1_packages)
        
        repo2_packages = [
            RepositoryPackage("pkg1", "1.0.0", "core", "x86_64"),
            RepositoryPackage("pkg3", "3.0.0", "extra", "x86_64")
        ]
        repo2 = Repository("repo-2", "endpoint-2", "core", packages=repo2_packages)
        
        mock_endpoint_repository.list_by_pool.return_value = endpoints
        mock_repo_repository.list_by_endpoint.side_effect = [
            [repo1], [repo2]
        ]
        
        result = await repository_analyzer.get_pool_package_matrix("pool-1")
        
        # Verify matrix structure
        assert "pkg1" in result
        assert "pkg2" in result
        assert "pkg3" in result
        
        # pkg1 is available on both endpoints
        assert result["pkg1"]["endpoint-1"] == "1.0.0"
        assert result["pkg1"]["endpoint-2"] == "1.0.0"
        
        # pkg2 is only available on endpoint-1
        assert result["pkg2"]["endpoint-1"] == "2.0.0"
        assert result["pkg2"]["endpoint-2"] is None
        
        # pkg3 is only available on endpoint-2
        assert result["pkg3"]["endpoint-1"] is None
        assert result["pkg3"]["endpoint-2"] == "3.0.0"
    
    @pytest.mark.asyncio
    async def test_get_pool_package_matrix_no_endpoints(self, repository_analyzer, 
                                                       mock_endpoint_repository):
        """Test package matrix generation with no endpoints."""
        mock_endpoint_repository.list_by_pool.return_value = []
        
        result = await repository_analyzer.get_pool_package_matrix("pool-1")
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_excluded_packages_for_pool_success(self, repository_analyzer):
        """Test successful excluded packages retrieval."""
        excluded_packages = [
            RepositoryPackage("excluded-pkg", "1.0.0", "core", "x86_64")
        ]
        
        mock_analysis = CompatibilityAnalysis(
            pool_id="pool-1",
            common_packages=[],
            excluded_packages=excluded_packages,
            conflicts=[]
        )
        
        with patch.object(repository_analyzer, 'analyze_pool_compatibility', 
                                     return_value=mock_analysis):
            result = await repository_analyzer.get_excluded_packages_for_pool("pool-1")
        
        assert result == excluded_packages
    
    def test_categorize_packages_all_common(self, repository_analyzer):
        """Test package categorization when all packages are common."""
        # Create package availability data
        package_availability = {
            "pkg1": PackageAvailability("pkg1"),
            "pkg2": PackageAvailability("pkg2")
        }
        
        # Add same package to both endpoints
        pkg1_package = RepositoryPackage("pkg1", "1.0.0", "core", "x86_64")
        pkg2_package = RepositoryPackage("pkg2", "2.0.0", "extra", "x86_64")
        
        package_availability["pkg1"].add_endpoint_package("endpoint-1", pkg1_package)
        package_availability["pkg1"].add_endpoint_package("endpoint-2", pkg1_package)
        package_availability["pkg2"].add_endpoint_package("endpoint-1", pkg2_package)
        package_availability["pkg2"].add_endpoint_package("endpoint-2", pkg2_package)
        
        endpoints = [
            Endpoint("endpoint-1", "Endpoint 1", "host1"),
            Endpoint("endpoint-2", "Endpoint 2", "host2")
        ]
        
        common_packages, excluded_packages = repository_analyzer._categorize_packages(
            package_availability, endpoints, []
        )
        
        assert len(common_packages) == 2
        assert len(excluded_packages) == 0
        
        common_names = [pkg.name for pkg in common_packages]
        assert "pkg1" in common_names
        assert "pkg2" in common_names
    
    def test_categorize_packages_with_exclusions(self, repository_analyzer):
        """Test package categorization with policy exclusions."""
        package_availability = {
            "pkg1": PackageAvailability("pkg1"),
            "excluded-pkg": PackageAvailability("excluded-pkg")
        }
        
        # Add packages to both endpoints
        pkg1_package = RepositoryPackage("pkg1", "1.0.0", "core", "x86_64")
        excluded_package = RepositoryPackage("excluded-pkg", "1.0.0", "core", "x86_64")
        
        for pkg_name, availability in package_availability.items():
            package = pkg1_package if pkg_name == "pkg1" else excluded_package
            availability.add_endpoint_package("endpoint-1", package)
            availability.add_endpoint_package("endpoint-2", package)
        
        endpoints = [
            Endpoint("endpoint-1", "Endpoint 1", "host1"),
            Endpoint("endpoint-2", "Endpoint 2", "host2")
        ]
        
        common_packages, excluded_packages = repository_analyzer._categorize_packages(
            package_availability, endpoints, ["excluded-pkg"]
        )
        
        assert len(common_packages) == 1
        assert len(excluded_packages) == 1
        
        assert common_packages[0].name == "pkg1"
        assert excluded_packages[0].name == "excluded-pkg"
        assert "Excluded by sync policy" in excluded_packages[0].description
    
    def test_categorize_packages_with_conflicts(self, repository_analyzer):
        """Test package categorization with version conflicts."""
        package_availability = {
            "conflict-pkg": PackageAvailability("conflict-pkg")
        }
        
        # Add different versions to different endpoints
        pkg1_v1 = RepositoryPackage("conflict-pkg", "1.0.0", "core", "x86_64")
        pkg1_v2 = RepositoryPackage("conflict-pkg", "2.0.0", "core", "x86_64")
        
        package_availability["conflict-pkg"].add_endpoint_package("endpoint-1", pkg1_v1)
        package_availability["conflict-pkg"].add_endpoint_package("endpoint-2", pkg1_v2)
        
        endpoints = [
            Endpoint("endpoint-1", "Endpoint 1", "host1"),
            Endpoint("endpoint-2", "Endpoint 2", "host2")
        ]
        
        common_packages, excluded_packages = repository_analyzer._categorize_packages(
            package_availability, endpoints, []
        )
        
        assert len(common_packages) == 0
        assert len(excluded_packages) == 1
        
        assert excluded_packages[0].name == "conflict-pkg"
        assert "Version conflicts" in excluded_packages[0].description
    
    def test_categorize_packages_missing_from_endpoints(self, repository_analyzer):
        """Test package categorization with packages missing from some endpoints."""
        package_availability = {
            "missing-pkg": PackageAvailability("missing-pkg")
        }
        
        # Add package to only one endpoint
        missing_package = RepositoryPackage("missing-pkg", "1.0.0", "core", "x86_64")
        package_availability["missing-pkg"].add_endpoint_package("endpoint-1", missing_package)
        
        endpoints = [
            Endpoint("endpoint-1", "Endpoint 1", "host1"),
            Endpoint("endpoint-2", "Endpoint 2", "host2")
        ]
        
        common_packages, excluded_packages = repository_analyzer._categorize_packages(
            package_availability, endpoints, []
        )
        
        assert len(common_packages) == 0
        assert len(excluded_packages) == 1
        
        assert excluded_packages[0].name == "missing-pkg"
        assert "Missing from 1 endpoint(s)" in excluded_packages[0].description
    
    def test_identify_conflicts(self, repository_analyzer):
        """Test conflict identification."""
        package_availability = {
            "no-conflict": PackageAvailability("no-conflict"),
            "has-conflict": PackageAvailability("has-conflict"),
            "missing-pkg": PackageAvailability("missing-pkg")
        }
        
        # No conflict package - same version on all endpoints
        no_conflict_pkg = RepositoryPackage("no-conflict", "1.0.0", "core", "x86_64")
        package_availability["no-conflict"].add_endpoint_package("endpoint-1", no_conflict_pkg)
        package_availability["no-conflict"].add_endpoint_package("endpoint-2", no_conflict_pkg)
        
        # Conflict package - different versions
        conflict_pkg_v1 = RepositoryPackage("has-conflict", "1.0.0", "core", "x86_64")
        conflict_pkg_v2 = RepositoryPackage("has-conflict", "2.0.0", "core", "x86_64")
        package_availability["has-conflict"].add_endpoint_package("endpoint-1", conflict_pkg_v1)
        package_availability["has-conflict"].add_endpoint_package("endpoint-2", conflict_pkg_v2)
        
        # Missing package - only on one endpoint (should not be in conflicts)
        missing_pkg = RepositoryPackage("missing-pkg", "1.0.0", "core", "x86_64")
        package_availability["missing-pkg"].add_endpoint_package("endpoint-1", missing_pkg)
        
        endpoints = [
            Endpoint("endpoint-1", "Endpoint 1", "host1"),
            Endpoint("endpoint-2", "Endpoint 2", "host2")
        ]
        
        conflicts = repository_analyzer._identify_conflicts(package_availability, endpoints)
        
        assert len(conflicts) == 1
        assert conflicts[0].package_name == "has-conflict"
        assert conflicts[0].endpoint_versions == {"endpoint-1": "1.0.0", "endpoint-2": "2.0.0"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])