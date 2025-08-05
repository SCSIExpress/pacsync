"""
Pacman interface for package state detection and repository analysis.

This module provides functionality to interact with pacman, parse its output,
detect package states, and extract repository information.
"""

import subprocess
import re
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from shared.models import PackageState, SystemState, RepositoryPackage, Repository

logger = logging.getLogger(__name__)


@dataclass
class PacmanConfig:
    """Configuration extracted from pacman.conf"""
    architecture: str
    repositories: List[Dict[str, str]]  # [{"name": "core", "server": "url"}, ...]
    cache_dir: str
    db_path: str
    log_file: str


class PacmanInterface:
    """Interface for interacting with pacman package manager."""
    
    def __init__(self):
        self.config = self._parse_pacman_config()
        self.pacman_version = self._get_pacman_version()
    
    def get_installed_packages(self) -> List[PackageState]:
        """
        Get all currently installed packages with their states.
        
        Returns:
            List of PackageState objects representing installed packages
            
        Raises:
            subprocess.CalledProcessError: If pacman command fails
            ValueError: If package parsing fails
        """
        try:
            # Get detailed package information
            cmd = ["pacman", "-Qi"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            packages = []
            current_package = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    if current_package:
                        packages.append(self._parse_package_info(current_package))
                        current_package = {}
                    continue
                
                if ':' in line:
                    key, value = line.split(':', 1)
                    current_package[key.strip()] = value.strip()
            
            # Handle last package if file doesn't end with empty line
            if current_package:
                packages.append(self._parse_package_info(current_package))
            
            logger.info(f"Retrieved {len(packages)} installed packages")
            return packages
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get installed packages: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing package information: {e}")
            raise ValueError(f"Failed to parse package information: {e}")
    
    def get_system_state(self, endpoint_id: str) -> SystemState:
        """
        Get complete system state including all packages.
        
        Args:
            endpoint_id: Unique identifier for this endpoint
            
        Returns:
            SystemState object with complete package information
        """
        packages = self.get_installed_packages()
        
        return SystemState(
            endpoint_id=endpoint_id,
            timestamp=datetime.now(),
            packages=packages,
            pacman_version=self.pacman_version,
            architecture=self.config.architecture
        )
    
    def get_repository_packages(self, repo_name: str) -> List[RepositoryPackage]:
        """
        Get all packages available in a specific repository.
        
        Args:
            repo_name: Name of the repository (e.g., 'core', 'extra', 'community')
            
        Returns:
            List of RepositoryPackage objects
            
        Raises:
            subprocess.CalledProcessError: If pacman command fails
        """
        try:
            # Get packages from specific repository
            cmd = ["pacman", "-Sl", repo_name]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            packages = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    repo = parts[0]
                    name = parts[1]
                    version = parts[2]
                    
                    # Check if package is installed (marked with [installed])
                    description = ' '.join(parts[3:]) if len(parts) > 3 else ""
                    
                    packages.append(RepositoryPackage(
                        name=name,
                        version=version,
                        repository=repo,
                        architecture=self.config.architecture,
                        description=description
                    ))
            
            logger.info(f"Retrieved {len(packages)} packages from repository {repo_name}")
            return packages
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get packages from repository {repo_name}: {e}")
            raise
    
    def get_all_repositories(self, endpoint_id: str) -> List[Repository]:
        """
        Get information about all configured repositories.
        
        Args:
            endpoint_id: Unique identifier for this endpoint
            
        Returns:
            List of Repository objects with package information
        """
        repositories = []
        
        for repo_config in self.config.repositories:
            repo_name = repo_config["name"]
            repo_url = repo_config.get("server", "")
            
            try:
                packages = self.get_repository_packages(repo_name)
                
                repository = Repository(
                    id="",  # Will be set by server
                    endpoint_id=endpoint_id,
                    repo_name=repo_name,
                    repo_url=repo_url,
                    packages=packages,
                    last_updated=datetime.now()
                )
                
                repositories.append(repository)
                
            except Exception as e:
                logger.warning(f"Failed to get packages for repository {repo_name}: {e}")
                # Create repository entry without packages
                repository = Repository(
                    id="",
                    endpoint_id=endpoint_id,
                    repo_name=repo_name,
                    repo_url=repo_url,
                    packages=[],
                    last_updated=datetime.now()
                )
                repositories.append(repository)
        
        logger.info(f"Retrieved information for {len(repositories)} repositories")
        return repositories
    
    def compare_package_states(self, current_state: SystemState, target_state: SystemState) -> Dict[str, str]:
        """
        Compare two system states and determine differences.
        
        Args:
            current_state: Current system package state
            target_state: Target system package state to compare against
            
        Returns:
            Dictionary mapping package names to their difference status:
            - 'newer': current version is newer than target
            - 'older': current version is older than target
            - 'missing': package exists in target but not in current
            - 'extra': package exists in current but not in target
            - 'same': versions are identical
        """
        current_packages = {pkg.package_name: pkg for pkg in current_state.packages}
        target_packages = {pkg.package_name: pkg for pkg in target_state.packages}
        
        differences = {}
        
        # Check packages in current state
        for name, current_pkg in current_packages.items():
            if name in target_packages:
                target_pkg = target_packages[name]
                version_comparison = self._compare_versions(current_pkg.version, target_pkg.version)
                
                if version_comparison > 0:
                    differences[name] = 'newer'
                elif version_comparison < 0:
                    differences[name] = 'older'
                else:
                    differences[name] = 'same'
            else:
                differences[name] = 'extra'
        
        # Check packages only in target state
        for name in target_packages:
            if name not in current_packages:
                differences[name] = 'missing'
        
        return differences
    
    def _parse_pacman_config(self) -> PacmanConfig:
        """Parse pacman.conf to extract configuration."""
        config_path = "/etc/pacman.conf"
        repositories = []
        architecture = "x86_64"  # default
        cache_dir = "/var/cache/pacman/pkg"
        db_path = "/var/lib/pacman"
        log_file = "/var/log/pacman.log"
        
        try:
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Extract architecture
            arch_match = re.search(r'^Architecture\s*=\s*(.+)$', content, re.MULTILINE)
            if arch_match:
                architecture = arch_match.group(1).strip()
            
            # Extract cache directory
            cache_match = re.search(r'^CacheDir\s*=\s*(.+)$', content, re.MULTILINE)
            if cache_match:
                cache_dir = cache_match.group(1).strip()
            
            # Extract database path
            db_match = re.search(r'^DBPath\s*=\s*(.+)$', content, re.MULTILINE)
            if db_match:
                db_path = db_match.group(1).strip()
            
            # Extract log file
            log_match = re.search(r'^LogFile\s*=\s*(.+)$', content, re.MULTILINE)
            if log_match:
                log_file = log_match.group(1).strip()
            
            # Extract repositories - handle both Server and Include directives
            lines = content.split('\n')
            current_repo = None
            
            for line in lines:
                line = line.strip()
                
                # Check for repository section
                repo_match = re.match(r'^\[([^\]]+)\]$', line)
                if repo_match:
                    repo_name = repo_match.group(1)
                    if repo_name != 'options':  # Skip [options] section
                        current_repo = repo_name
                    else:
                        current_repo = None
                    continue
                
                # Check for Server or Include directive
                if current_repo and not line.startswith('#'):
                    server_match = re.match(r'^Server\s*=\s*(.+)$', line)
                    include_match = re.match(r'^Include\s*=\s*(.+)$', line)
                    
                    if server_match:
                        repositories.append({
                            "name": current_repo,
                            "server": server_match.group(1).strip()
                        })
                    elif include_match:
                        # For Include directives, we'll use a placeholder URL
                        # In a real implementation, we could parse the mirrorlist file
                        repositories.append({
                            "name": current_repo,
                            "server": f"mirrorlist:{include_match.group(1).strip()}"
                        })
            
        except Exception as e:
            logger.warning(f"Failed to parse pacman.conf: {e}. Using defaults.")
            # Use common default repositories
            repositories = [
                {"name": "core", "server": "https://mirror.archlinux.org/core/os/x86_64"},
                {"name": "extra", "server": "https://mirror.archlinux.org/extra/os/x86_64"},
                {"name": "community", "server": "https://mirror.archlinux.org/community/os/x86_64"}
            ]
        
        return PacmanConfig(
            architecture=architecture,
            repositories=repositories,
            cache_dir=cache_dir,
            db_path=db_path,
            log_file=log_file
        )
    
    def _get_pacman_version(self) -> str:
        """Get pacman version."""
        try:
            result = subprocess.run(["pacman", "--version"], 
                                  capture_output=True, text=True, check=True)
            # Extract version from output (e.g., "Pacman v6.0.1 - libalpm v13.0.1")
            version_match = re.search(r'Pacman v([\d.]+)', result.stdout)
            if version_match:
                return version_match.group(1)
            return "unknown"
        except Exception as e:
            logger.warning(f"Failed to get pacman version: {e}")
            return "unknown"
    
    def _parse_package_info(self, package_info: Dict[str, str]) -> PackageState:
        """Parse package information from pacman -Qi output."""
        name = package_info.get('Name', '')
        version = package_info.get('Version', '')
        repository = package_info.get('Repository', 'local')
        
        # Parse installed size (convert to bytes)
        size_str = package_info.get('Installed Size', '0')
        installed_size = self._parse_size_to_bytes(size_str)
        
        # Parse dependencies
        depends_str = package_info.get('Depends On', '')
        dependencies = []
        if depends_str and depends_str != 'None':
            # Split dependencies and clean up version constraints
            deps = depends_str.split()
            for dep in deps:
                # Remove version constraints (e.g., "glibc>=2.33" -> "glibc")
                clean_dep = re.sub(r'[<>=].*', '', dep)
                if clean_dep:
                    dependencies.append(clean_dep)
        
        return PackageState(
            package_name=name,
            version=version,
            repository=repository,
            installed_size=installed_size,
            dependencies=dependencies
        )
    
    def _parse_size_to_bytes(self, size_str: str) -> int:
        """Convert size string to bytes (e.g., '1.5 MiB' -> bytes)."""
        if not size_str or size_str == '0':
            return 0
        
        # Remove any extra whitespace
        size_str = size_str.strip()
        
        # Extract number and unit
        match = re.match(r'([\d.]+)\s*([KMGT]?i?B?)', size_str)
        if not match:
            return 0
        
        number = float(match.group(1))
        unit = match.group(2).upper()
        
        # Convert to bytes
        multipliers = {
            'B': 1,
            'KB': 1000, 'KIB': 1024,
            'MB': 1000**2, 'MIB': 1024**2,
            'GB': 1000**3, 'GIB': 1024**3,
            'TB': 1000**4, 'TIB': 1024**4
        }
        
        multiplier = multipliers.get(unit, 1)
        return int(number * multiplier)
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings using pacman's version comparison.
        
        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        try:
            # Use pacman's vercmp utility for accurate version comparison
            result = subprocess.run(["vercmp", version1, version2], 
                                  capture_output=True, text=True, check=True)
            return int(result.stdout.strip())
        except Exception:
            # Fallback to simple string comparison if vercmp fails
            if version1 == version2:
                return 0
            elif version1 > version2:
                return 1
            else:
                return -1


class PackageStateDetector:
    """Utility class for detecting and comparing package states."""
    
    def __init__(self, pacman_interface: PacmanInterface):
        self.pacman = pacman_interface
    
    def detect_sync_status(self, current_state: SystemState, target_state: Optional[SystemState]) -> str:
        """
        Detect synchronization status by comparing current state with target.
        
        Args:
            current_state: Current system state
            target_state: Target state to compare against (None if no target set)
            
        Returns:
            Sync status: 'in_sync', 'ahead', 'behind', or 'unknown'
        """
        if not target_state:
            return 'unknown'
        
        differences = self.pacman.compare_package_states(current_state, target_state)
        
        has_newer = any(status == 'newer' for status in differences.values())
        has_older = any(status == 'older' for status in differences.values())
        has_missing = any(status == 'missing' for status in differences.values())
        has_extra = any(status == 'extra' for status in differences.values())
        
        if not has_newer and not has_older and not has_missing and not has_extra:
            return 'in_sync'
        elif has_newer or has_extra:
            return 'ahead'
        elif has_older or has_missing:
            return 'behind'
        else:
            return 'unknown'
    
    def get_package_changes(self, current_state: SystemState, target_state: SystemState) -> Dict[str, List[str]]:
        """
        Get detailed package changes needed to reach target state.
        
        Returns:
            Dictionary with lists of packages to install, upgrade, downgrade, remove
        """
        differences = self.pacman.compare_package_states(current_state, target_state)
        
        changes = {
            'install': [],    # Packages to install (missing in current)
            'upgrade': [],    # Packages to upgrade (older in current)
            'downgrade': [],  # Packages to downgrade (newer in current)
            'remove': []      # Packages to remove (extra in current)
        }
        
        for package_name, status in differences.items():
            if status == 'missing':
                changes['install'].append(package_name)
            elif status == 'older':
                changes['upgrade'].append(package_name)
            elif status == 'newer':
                changes['downgrade'].append(package_name)
            elif status == 'extra':
                changes['remove'].append(package_name)
        
        return changes