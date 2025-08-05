"""
Repository Analysis Service for the Pacman Sync Utility.

This module implements the RepositoryAnalyzer class that processes repository
information from endpoints, analyzes package compatibility across pool endpoints,
and automatically excludes packages not available in all repositories.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Set, Tuple
from collections import defaultdict

from shared.models import (
    CompatibilityAnalysis, Repository, RepositoryPackage, PackageConflict,
    PackagePool, Endpoint
)
from shared.interfaces import IRepositoryAnalyzer
from server.database.orm import RepositoryRepository, PoolRepository, EndpointRepository
from server.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class PackageAvailability:
    """Tracks package availability across endpoints in a pool."""
    
    def __init__(self, package_name: str):
        self.package_name = package_name
        self.endpoint_versions: Dict[str, str] = {}  # endpoint_id -> version
        self.endpoint_repositories: Dict[str, str] = {}  # endpoint_id -> repository
        self.endpoint_architectures: Dict[str, str] = {}  # endpoint_id -> architecture
    
    def add_endpoint_package(self, endpoint_id: str, package: RepositoryPackage):
        """Add package information from an endpoint."""
        self.endpoint_versions[endpoint_id] = package.version
        self.endpoint_repositories[endpoint_id] = package.repository
        self.endpoint_architectures[endpoint_id] = package.architecture
    
    @property
    def available_endpoints(self) -> Set[str]:
        """Get set of endpoints where this package is available."""
        return set(self.endpoint_versions.keys())
    
    @property
    def unique_versions(self) -> Set[str]:
        """Get set of unique versions across endpoints."""
        return set(self.endpoint_versions.values())
    
    @property
    def has_version_conflicts(self) -> bool:
        """Check if there are version conflicts across endpoints."""
        return len(self.unique_versions) > 1
    
    def get_most_common_version(self) -> str:
        """Get the most common version across endpoints."""
        if not self.endpoint_versions:
            return ""
        
        version_counts = defaultdict(int)
        for version in self.endpoint_versions.values():
            version_counts[version] += 1
        
        return max(version_counts.items(), key=lambda x: x[1])[0]
    
    def create_conflict(self) -> PackageConflict:
        """Create a PackageConflict object for this package."""
        suggested_resolution = f"Use version {self.get_most_common_version()} (most common)"
        
        return PackageConflict(
            package_name=self.package_name,
            endpoint_versions=self.endpoint_versions.copy(),
            suggested_resolution=suggested_resolution
        )


class RepositoryAnalyzer(IRepositoryAnalyzer):
    """
    Analyzes repository compatibility across pool endpoints and manages
    package exclusions based on availability.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.repo_repository = RepositoryRepository(db_manager)
        self.pool_repository = PoolRepository(db_manager)
        self.endpoint_repository = EndpointRepository(db_manager)
        logger.info("RepositoryAnalyzer initialized")
    
    async def analyze_pool_compatibility(self, pool_id: str) -> CompatibilityAnalysis:
        """
        Analyze package compatibility across all endpoints in a pool.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            CompatibilityAnalysis with common packages, excluded packages, and conflicts
        """
        logger.info(f"Starting compatibility analysis for pool: {pool_id}")
        
        try:
            # Get pool and its endpoints
            pool = await self.pool_repository.get_by_id(pool_id)
            if not pool:
                logger.error(f"Pool not found: {pool_id}")
                return CompatibilityAnalysis(
                    pool_id=pool_id,
                    common_packages=[],
                    excluded_packages=[],
                    conflicts=[]
                )
            
            endpoints = await self.endpoint_repository.list_by_pool(pool_id)
            if not endpoints:
                logger.warning(f"No endpoints found in pool: {pool_id}")
                return CompatibilityAnalysis(
                    pool_id=pool_id,
                    common_packages=[],
                    excluded_packages=[],
                    conflicts=[]
                )
            
            logger.debug(f"Analyzing {len(endpoints)} endpoints in pool {pool_id}")
            
            # Collect all repository information for endpoints
            all_packages = await self._collect_endpoint_packages(endpoints)
            
            # Analyze package availability
            package_availability = self._analyze_package_availability(all_packages, endpoints)
            
            # Determine common and excluded packages
            common_packages, excluded_packages = self._categorize_packages(
                package_availability, endpoints, pool.sync_policy.exclude_packages
            )
            
            # Identify conflicts
            conflicts = self._identify_conflicts(package_availability, endpoints)
            
            analysis = CompatibilityAnalysis(
                pool_id=pool_id,
                common_packages=common_packages,
                excluded_packages=excluded_packages,
                conflicts=conflicts,
                last_analyzed=datetime.now()
            )
            
            logger.info(
                f"Compatibility analysis complete for pool {pool_id}: "
                f"{len(common_packages)} common, {len(excluded_packages)} excluded, "
                f"{len(conflicts)} conflicts"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing pool compatibility for {pool_id}: {e}")
            return CompatibilityAnalysis(
                pool_id=pool_id,
                common_packages=[],
                excluded_packages=[],
                conflicts=[]
            )
    
    async def update_repository_info(self, endpoint_id: str, repositories: List[Repository]) -> bool:
        """
        Update repository information for an endpoint.
        
        Args:
            endpoint_id: Endpoint identifier
            repositories: List of repository information
            
        Returns:
            True if updated successfully, False otherwise
        """
        logger.info(f"Updating repository info for endpoint: {endpoint_id}")
        
        try:
            # Verify endpoint exists
            endpoint = await self.endpoint_repository.get_by_id(endpoint_id)
            if not endpoint:
                logger.error(f"Endpoint not found: {endpoint_id}")
                return False
            
            # Delete existing repository information
            await self.repo_repository.delete_by_endpoint(endpoint_id)
            
            # Create new repository records
            for repo in repositories:
                # Ensure endpoint_id is set correctly
                repo.endpoint_id = endpoint_id
                repo.last_updated = datetime.now()
                
                await self.repo_repository.create_or_update(repo)
                logger.debug(f"Updated repository {repo.repo_name} for endpoint {endpoint_id}")
            
            logger.info(f"Successfully updated {len(repositories)} repositories for endpoint {endpoint_id}")
            
            # If endpoint is in a pool, trigger compatibility analysis
            if endpoint.pool_id:
                logger.debug(f"Triggering compatibility analysis for pool {endpoint.pool_id}")
                await self.analyze_pool_compatibility(endpoint.pool_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating repository info for endpoint {endpoint_id}: {e}")
            return False
    
    async def get_repository_info(self, endpoint_id: str) -> List[Repository]:
        """
        Get repository information for an endpoint.
        
        Args:
            endpoint_id: Endpoint identifier
            
        Returns:
            List of Repository objects
        """
        try:
            repositories = await self.repo_repository.list_by_endpoint(endpoint_id)
            logger.debug(f"Retrieved {len(repositories)} repositories for endpoint {endpoint_id}")
            return repositories
        except Exception as e:
            logger.error(f"Error getting repository info for endpoint {endpoint_id}: {e}")
            return []
    
    async def get_pool_package_matrix(self, pool_id: str) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Get a matrix showing package availability across all endpoints in a pool.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            Dictionary mapping package_name -> endpoint_id -> version (or None if not available)
        """
        logger.debug(f"Generating package matrix for pool: {pool_id}")
        
        try:
            endpoints = await self.endpoint_repository.list_by_pool(pool_id)
            if not endpoints:
                return {}
            
            all_packages = await self._collect_endpoint_packages(endpoints)
            package_availability = self._analyze_package_availability(all_packages, endpoints)
            
            matrix = {}
            for package_name, availability in package_availability.items():
                matrix[package_name] = {}
                for endpoint in endpoints:
                    if endpoint.id in availability.endpoint_versions:
                        matrix[package_name][endpoint.id] = availability.endpoint_versions[endpoint.id]
                    else:
                        matrix[package_name][endpoint.id] = None
            
            logger.debug(f"Generated matrix with {len(matrix)} packages for {len(endpoints)} endpoints")
            return matrix
            
        except Exception as e:
            logger.error(f"Error generating package matrix for pool {pool_id}: {e}")
            return {}
    
    async def get_excluded_packages_for_pool(self, pool_id: str) -> List[RepositoryPackage]:
        """
        Get packages that are excluded from synchronization for a pool.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            List of excluded RepositoryPackage objects
        """
        try:
            analysis = await self.analyze_pool_compatibility(pool_id)
            return analysis.excluded_packages
        except Exception as e:
            logger.error(f"Error getting excluded packages for pool {pool_id}: {e}")
            return []
    
    async def _collect_endpoint_packages(self, endpoints: List[Endpoint]) -> Dict[str, List[RepositoryPackage]]:
        """
        Collect all packages from all repositories for the given endpoints.
        
        Args:
            endpoints: List of endpoints
            
        Returns:
            Dictionary mapping endpoint_id to list of all packages
        """
        all_packages = {}
        
        for endpoint in endpoints:
            endpoint_packages = []
            repositories = await self.repo_repository.list_by_endpoint(endpoint.id)
            
            for repo in repositories:
                endpoint_packages.extend(repo.packages)
            
            all_packages[endpoint.id] = endpoint_packages
            logger.debug(f"Collected {len(endpoint_packages)} packages from endpoint {endpoint.id}")
        
        return all_packages
    
    def _analyze_package_availability(self, all_packages: Dict[str, List[RepositoryPackage]], 
                                    endpoints: List[Endpoint]) -> Dict[str, PackageAvailability]:
        """
        Analyze package availability across endpoints.
        
        Args:
            all_packages: Dictionary mapping endpoint_id to list of packages
            endpoints: List of endpoints
            
        Returns:
            Dictionary mapping package_name to PackageAvailability
        """
        package_availability = {}
        
        # Process each endpoint's packages
        for endpoint in endpoints:
            endpoint_packages = all_packages.get(endpoint.id, [])
            
            for package in endpoint_packages:
                if package.name not in package_availability:
                    package_availability[package.name] = PackageAvailability(package.name)
                
                package_availability[package.name].add_endpoint_package(endpoint.id, package)
        
        logger.debug(f"Analyzed availability for {len(package_availability)} unique packages")
        return package_availability
    
    def _categorize_packages(self, package_availability: Dict[str, PackageAvailability],
                           endpoints: List[Endpoint], 
                           policy_excluded: List[str]) -> Tuple[List[RepositoryPackage], List[RepositoryPackage]]:
        """
        Categorize packages into common (available on all endpoints) and excluded.
        
        Args:
            package_availability: Package availability analysis
            endpoints: List of endpoints
            policy_excluded: Packages excluded by sync policy
            
        Returns:
            Tuple of (common_packages, excluded_packages)
        """
        endpoint_ids = {endpoint.id for endpoint in endpoints}
        common_packages = []
        excluded_packages = []
        
        for package_name, availability in package_availability.items():
            # Check if package is excluded by policy
            if package_name in policy_excluded:
                # Create a representative package for the excluded list
                if availability.endpoint_versions:
                    first_endpoint = next(iter(availability.endpoint_versions.keys()))
                    excluded_packages.append(RepositoryPackage(
                        name=package_name,
                        version=availability.endpoint_versions[first_endpoint],
                        repository=availability.endpoint_repositories[first_endpoint],
                        architecture=availability.endpoint_architectures[first_endpoint],
                        description=f"Excluded by sync policy"
                    ))
                continue
            
            # Check if package is available on all endpoints
            if availability.available_endpoints == endpoint_ids:
                # Only include as common if there are no version conflicts
                if not availability.has_version_conflicts:
                    # Package is common and has consistent version
                    common_version = availability.get_most_common_version()
                    
                    # Find an endpoint with this version to get repository info
                    representative_endpoint = None
                    for endpoint_id, version in availability.endpoint_versions.items():
                        if version == common_version:
                            representative_endpoint = endpoint_id
                            break
                    
                    if representative_endpoint:
                        common_packages.append(RepositoryPackage(
                            name=package_name,
                            version=common_version,
                            repository=availability.endpoint_repositories[representative_endpoint],
                            architecture=availability.endpoint_architectures[representative_endpoint],
                            description=f"Available on all {len(endpoints)} endpoints"
                        ))
                else:
                    # Package has version conflicts - exclude it
                    first_endpoint = next(iter(availability.endpoint_versions.keys()))
                    excluded_packages.append(RepositoryPackage(
                        name=package_name,
                        version=availability.endpoint_versions[first_endpoint],
                        repository=availability.endpoint_repositories[first_endpoint],
                        architecture=availability.endpoint_architectures[first_endpoint],
                        description=f"Version conflicts across endpoints"
                    ))
            else:
                # Package is not available on all endpoints - exclude it
                missing_count = len(endpoint_ids) - len(availability.available_endpoints)
                
                if availability.endpoint_versions:
                    first_endpoint = next(iter(availability.endpoint_versions.keys()))
                    excluded_packages.append(RepositoryPackage(
                        name=package_name,
                        version=availability.endpoint_versions[first_endpoint],
                        repository=availability.endpoint_repositories[first_endpoint],
                        architecture=availability.endpoint_architectures[first_endpoint],
                        description=f"Missing from {missing_count} endpoint(s)"
                    ))
        
        logger.debug(f"Categorized {len(common_packages)} common and {len(excluded_packages)} excluded packages")
        return common_packages, excluded_packages
    
    def _identify_conflicts(self, package_availability: Dict[str, PackageAvailability],
                          endpoints: List[Endpoint]) -> List[PackageConflict]:
        """
        Identify version conflicts in common packages.
        
        Args:
            package_availability: Package availability analysis
            endpoints: List of endpoints
            
        Returns:
            List of PackageConflict objects
        """
        endpoint_ids = {endpoint.id for endpoint in endpoints}
        conflicts = []
        
        for package_name, availability in package_availability.items():
            # Only check conflicts for packages available on all endpoints
            if availability.available_endpoints == endpoint_ids and availability.has_version_conflicts:
                conflicts.append(availability.create_conflict())
        
        logger.debug(f"Identified {len(conflicts)} version conflicts")
        return conflicts