"""
Repository Analysis API endpoints for the Pacman Sync Utility.

This module implements FastAPI endpoints for repository compatibility analysis,
package exclusion management, and repository information visualization.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from shared.models import CompatibilityAnalysis, RepositoryPackage, PackageConflict
from server.core.repository_analyzer import RepositoryAnalyzer

logger = logging.getLogger(__name__)
router = APIRouter()


# Response Models
class RepositoryPackageResponse(BaseModel):
    name: str
    version: str
    repository: str
    architecture: str
    description: Optional[str] = None


class PackageConflictResponse(BaseModel):
    package_name: str
    endpoint_versions: Dict[str, str]
    suggested_resolution: str


class CompatibilityAnalysisResponse(BaseModel):
    pool_id: str
    common_packages: List[RepositoryPackageResponse]
    excluded_packages: List[RepositoryPackageResponse]
    conflicts: List[PackageConflictResponse]
    last_analyzed: str


class PackageMatrixResponse(BaseModel):
    pool_id: str
    packages: Dict[str, Dict[str, Optional[str]]]  # package_name -> endpoint_id -> version
    endpoints: List[Dict[str, str]]  # endpoint info


class RepositoryInfoResponse(BaseModel):
    endpoint_id: str
    repositories: List[Dict[str, Any]]


# Dependency to get repository analyzer
async def get_repository_analyzer(request: Request) -> RepositoryAnalyzer:
    """Get repository analyzer from app state."""
    if not hasattr(request.app.state, 'repository_analyzer'):
        # Initialize repository analyzer if not exists
        db_manager = request.app.state.db_manager
        request.app.state.repository_analyzer = RepositoryAnalyzer(db_manager)
    return request.app.state.repository_analyzer


def package_to_response(package: RepositoryPackage) -> RepositoryPackageResponse:
    """Convert RepositoryPackage to response format."""
    return RepositoryPackageResponse(
        name=package.name,
        version=package.version,
        repository=package.repository,
        architecture=package.architecture,
        description=package.description
    )


def conflict_to_response(conflict: PackageConflict) -> PackageConflictResponse:
    """Convert PackageConflict to response format."""
    return PackageConflictResponse(
        package_name=conflict.package_name,
        endpoint_versions=conflict.endpoint_versions,
        suggested_resolution=conflict.suggested_resolution
    )


@router.get("/repositories/analysis/{pool_id}", response_model=CompatibilityAnalysisResponse)
async def get_pool_compatibility_analysis(
    pool_id: str,
    analyzer: RepositoryAnalyzer = Depends(get_repository_analyzer)
):
    """Get repository compatibility analysis for a pool."""
    try:
        logger.info(f"Getting compatibility analysis for pool: {pool_id}")
        
        analysis = await analyzer.analyze_pool_compatibility(pool_id)
        
        return CompatibilityAnalysisResponse(
            pool_id=analysis.pool_id,
            common_packages=[package_to_response(pkg) for pkg in analysis.common_packages],
            excluded_packages=[package_to_response(pkg) for pkg in analysis.excluded_packages],
            conflicts=[conflict_to_response(conflict) for conflict in analysis.conflicts],
            last_analyzed=analysis.last_analyzed.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to get compatibility analysis for pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analysis: {str(e)}")


@router.post("/repositories/analysis/{pool_id}/refresh")
async def refresh_pool_compatibility_analysis(
    pool_id: str,
    analyzer: RepositoryAnalyzer = Depends(get_repository_analyzer)
):
    """Refresh repository compatibility analysis for a pool."""
    try:
        logger.info(f"Refreshing compatibility analysis for pool: {pool_id}")
        
        analysis = await analyzer.analyze_pool_compatibility(pool_id)
        
        return {
            "message": "Analysis refreshed successfully",
            "pool_id": pool_id,
            "common_packages_count": len(analysis.common_packages),
            "excluded_packages_count": len(analysis.excluded_packages),
            "conflicts_count": len(analysis.conflicts),
            "last_analyzed": analysis.last_analyzed.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh compatibility analysis for pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh analysis: {str(e)}")


@router.get("/repositories/matrix/{pool_id}", response_model=PackageMatrixResponse)
async def get_package_availability_matrix(
    pool_id: str,
    analyzer: RepositoryAnalyzer = Depends(get_repository_analyzer),
    request: Request = None
):
    """Get package availability matrix for a pool."""
    try:
        logger.info(f"Getting package matrix for pool: {pool_id}")
        
        # Get the package matrix
        matrix = await analyzer.get_pool_package_matrix(pool_id)
        
        # Get endpoint information
        db_manager = request.app.state.db_manager
        from server.database.orm import EndpointRepository
        endpoint_repo = EndpointRepository(db_manager)
        endpoints = await endpoint_repo.list_by_pool(pool_id)
        
        endpoint_info = []
        for endpoint in endpoints:
            endpoint_info.append({
                "id": endpoint.id,
                "name": endpoint.name,
                "hostname": endpoint.hostname,
                "sync_status": endpoint.sync_status.value
            })
        
        return PackageMatrixResponse(
            pool_id=pool_id,
            packages=matrix,
            endpoints=endpoint_info
        )
        
    except Exception as e:
        logger.error(f"Failed to get package matrix for pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get package matrix: {str(e)}")


@router.get("/repositories/excluded/{pool_id}", response_model=List[RepositoryPackageResponse])
async def get_excluded_packages(
    pool_id: str,
    analyzer: RepositoryAnalyzer = Depends(get_repository_analyzer)
):
    """Get packages excluded from synchronization for a pool."""
    try:
        logger.info(f"Getting excluded packages for pool: {pool_id}")
        
        excluded_packages = await analyzer.get_excluded_packages_for_pool(pool_id)
        
        return [package_to_response(pkg) for pkg in excluded_packages]
        
    except Exception as e:
        logger.error(f"Failed to get excluded packages for pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get excluded packages: {str(e)}")


@router.get("/repositories/endpoint/{endpoint_id}", response_model=RepositoryInfoResponse)
async def get_endpoint_repository_info(
    endpoint_id: str,
    analyzer: RepositoryAnalyzer = Depends(get_repository_analyzer)
):
    """Get repository information for a specific endpoint."""
    try:
        logger.info(f"Getting repository info for endpoint: {endpoint_id}")
        
        repositories = await analyzer.get_repository_info(endpoint_id)
        
        repo_data = []
        for repo in repositories:
            packages_data = []
            for pkg in repo.packages:
                packages_data.append({
                    "name": pkg.name,
                    "version": pkg.version,
                    "repository": pkg.repository,
                    "architecture": pkg.architecture,
                    "description": pkg.description
                })
            
            repo_data.append({
                "id": repo.id,
                "repo_name": repo.repo_name,
                "repo_url": repo.repo_url,
                "packages": packages_data,
                "last_updated": repo.last_updated.isoformat()
            })
        
        return RepositoryInfoResponse(
            endpoint_id=endpoint_id,
            repositories=repo_data
        )
        
    except Exception as e:
        logger.error(f"Failed to get repository info for endpoint {endpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get repository info: {str(e)}")


@router.get("/repositories/conflicts/{pool_id}", response_model=List[PackageConflictResponse])
async def get_package_conflicts(
    pool_id: str,
    analyzer: RepositoryAnalyzer = Depends(get_repository_analyzer)
):
    """Get package version conflicts for a pool."""
    try:
        logger.info(f"Getting package conflicts for pool: {pool_id}")
        
        analysis = await analyzer.analyze_pool_compatibility(pool_id)
        
        return [conflict_to_response(conflict) for conflict in analysis.conflicts]
        
    except Exception as e:
        logger.error(f"Failed to get package conflicts for pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conflicts: {str(e)}")