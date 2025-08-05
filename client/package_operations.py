"""
Package Operations for Pacman Sync Utility.

This module implements the core package synchronization operations:
- sync-to-latest functionality: Install/remove packages to match target state
- set-as-latest operation: Capture current system state as new target
- revert-to-previous functionality: Restore packages to previous state

Requirements: 6.2, 6.3, 6.4, 11.3, 11.4
"""

import subprocess
import logging
import json
import tempfile
import os
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime

from shared.models import PackageState, SystemState, OperationType
from client.pacman_interface import PacmanInterface, PackageStateDetector

logger = logging.getLogger(__name__)


@dataclass
class PackageOperation:
    """Represents a single package operation to be performed."""
    operation_type: str  # 'install', 'remove', 'upgrade', 'downgrade'
    package_name: str
    current_version: Optional[str] = None
    target_version: Optional[str] = None
    repository: Optional[str] = None


@dataclass
class SyncResult:
    """Result of a synchronization operation."""
    success: bool
    operations_performed: List[PackageOperation]
    errors: List[str]
    warnings: List[str]
    packages_changed: int
    duration_seconds: float


class PackageOperationError(Exception):
    """Exception raised when package operations fail."""
    pass


class PackageSynchronizer:
    """
    Handles package synchronization operations using pacman.
    
    This class implements the core synchronization logic for:
    - Syncing to latest state
    - Setting current state as latest
    - Reverting to previous state
    """
    
    def __init__(self, pacman_interface: PacmanInterface):
        self.pacman = pacman_interface
        self.detector = PackageStateDetector(pacman_interface)
        self._dry_run = False
        
    def set_dry_run(self, dry_run: bool):
        """Enable/disable dry run mode for testing."""
        self._dry_run = dry_run
        
    def sync_to_latest(self, target_state: SystemState) -> SyncResult:
        """
        Synchronize packages to match the target state.
        
        This operation will:
        1. Compare current state with target state
        2. Install missing packages
        3. Upgrade/downgrade packages to target versions
        4. Remove extra packages not in target state
        
        Args:
            target_state: The desired system state to sync to
            
        Returns:
            SyncResult with operation details and success status
            
        Raises:
            PackageOperationError: If critical operations fail
        """
        start_time = datetime.now()
        logger.info(f"Starting sync to latest operation for {len(target_state.packages)} packages")
        
        try:
            # Get current system state
            current_state = self.pacman.get_system_state("current")
            
            # Calculate required operations
            operations = self._calculate_sync_operations(current_state, target_state)
            
            if not operations:
                logger.info("No package operations required - system already in sync")
                return SyncResult(
                    success=True,
                    operations_performed=[],
                    errors=[],
                    warnings=[],
                    packages_changed=0,
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            logger.info(f"Calculated {len(operations)} package operations")
            
            # Execute operations in proper order
            result = self._execute_operations(operations)
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Sync operation completed: success={result.success}, "
                       f"changed={result.packages_changed}, duration={result.duration_seconds:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Sync to latest operation failed: {e}")
            return SyncResult(
                success=False,
                operations_performed=[],
                errors=[str(e)],
                warnings=[],
                packages_changed=0,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    def set_as_latest(self, endpoint_id: str) -> Tuple[SystemState, SyncResult]:
        """
        Capture the current system state as the new latest state.
        
        This operation will:
        1. Get current package state
        2. Create a system state snapshot
        3. Return the state for server submission
        
        Args:
            endpoint_id: ID of the endpoint setting the state
            
        Returns:
            Tuple of (SystemState, SyncResult)
            
        Raises:
            PackageOperationError: If state capture fails
        """
        start_time = datetime.now()
        logger.info("Capturing current system state as latest")
        
        try:
            # Get current system state
            current_state = self.pacman.get_system_state(endpoint_id)
            
            logger.info(f"Captured state with {len(current_state.packages)} packages")
            
            result = SyncResult(
                success=True,
                operations_performed=[],
                errors=[],
                warnings=[],
                packages_changed=0,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
            
            return current_state, result
            
        except Exception as e:
            logger.error(f"Set as latest operation failed: {e}")
            result = SyncResult(
                success=False,
                operations_performed=[],
                errors=[str(e)],
                warnings=[],
                packages_changed=0,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
            return None, result
    
    def revert_to_previous(self, previous_state: SystemState) -> SyncResult:
        """
        Revert packages to a previous system state.
        
        This operation will:
        1. Compare current state with previous state
        2. Install/remove/upgrade/downgrade packages to match previous state
        3. Handle conflicts and missing packages gracefully
        
        Args:
            previous_state: The previous system state to revert to
            
        Returns:
            SyncResult with operation details and success status
            
        Raises:
            PackageOperationError: If critical revert operations fail
        """
        start_time = datetime.now()
        logger.info(f"Starting revert to previous state with {len(previous_state.packages)} packages")
        
        try:
            # Get current system state
            current_state = self.pacman.get_system_state("current")
            
            # Calculate required operations (same as sync, but to previous state)
            operations = self._calculate_sync_operations(current_state, previous_state)
            
            if not operations:
                logger.info("No package operations required - system already matches previous state")
                return SyncResult(
                    success=True,
                    operations_performed=[],
                    errors=[],
                    warnings=[],
                    packages_changed=0,
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            logger.info(f"Calculated {len(operations)} revert operations")
            
            # Execute operations with extra caution for reverts
            result = self._execute_operations(operations, is_revert=True)
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Revert operation completed: success={result.success}, "
                       f"changed={result.packages_changed}, duration={result.duration_seconds:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Revert to previous operation failed: {e}")
            return SyncResult(
                success=False,
                operations_performed=[],
                errors=[str(e)],
                warnings=[],
                packages_changed=0,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    def _calculate_sync_operations(self, current_state: SystemState, target_state: SystemState) -> List[PackageOperation]:
        """
        Calculate the package operations needed to sync current state to target state.
        
        Args:
            current_state: Current system package state
            target_state: Target system package state
            
        Returns:
            List of PackageOperation objects in execution order
        """
        operations = []
        
        # Get package differences
        differences = self.pacman.compare_package_states(current_state, target_state)
        
        current_packages = {pkg.package_name: pkg for pkg in current_state.packages}
        target_packages = {pkg.package_name: pkg for pkg in target_state.packages}
        
        # Process each difference
        for package_name, status in differences.items():
            if status == 'missing':
                # Package needs to be installed
                target_pkg = target_packages[package_name]
                operations.append(PackageOperation(
                    operation_type='install',
                    package_name=package_name,
                    target_version=target_pkg.version,
                    repository=target_pkg.repository
                ))
                
            elif status == 'extra':
                # Package needs to be removed
                current_pkg = current_packages[package_name]
                operations.append(PackageOperation(
                    operation_type='remove',
                    package_name=package_name,
                    current_version=current_pkg.version
                ))
                
            elif status == 'older':
                # Package needs to be upgraded
                current_pkg = current_packages[package_name]
                target_pkg = target_packages[package_name]
                operations.append(PackageOperation(
                    operation_type='upgrade',
                    package_name=package_name,
                    current_version=current_pkg.version,
                    target_version=target_pkg.version,
                    repository=target_pkg.repository
                ))
                
            elif status == 'newer':
                # Package needs to be downgraded
                current_pkg = current_packages[package_name]
                target_pkg = target_packages[package_name]
                operations.append(PackageOperation(
                    operation_type='downgrade',
                    package_name=package_name,
                    current_version=current_pkg.version,
                    target_version=target_pkg.version,
                    repository=target_pkg.repository
                ))
        
        # Sort operations by priority (removes first, then installs/upgrades)
        operations.sort(key=lambda op: {
            'remove': 0,
            'downgrade': 1,
            'upgrade': 2,
            'install': 3
        }.get(op.operation_type, 4))
        
        return operations
    
    def _execute_operations(self, operations: List[PackageOperation], is_revert: bool = False) -> SyncResult:
        """
        Execute a list of package operations.
        
        Args:
            operations: List of operations to execute
            is_revert: Whether this is a revert operation (affects error handling)
            
        Returns:
            SyncResult with execution details
        """
        executed_operations = []
        errors = []
        warnings = []
        packages_changed = 0
        
        # Group operations by type for batch execution
        operation_groups = self._group_operations(operations)
        
        for group_type, group_operations in operation_groups.items():
            if not group_operations:
                continue
                
            try:
                if group_type == 'remove':
                    success, group_errors = self._execute_remove_operations(group_operations)
                elif group_type == 'install':
                    success, group_errors = self._execute_install_operations(group_operations)
                elif group_type == 'upgrade':
                    success, group_errors = self._execute_upgrade_operations(group_operations)
                elif group_type == 'downgrade':
                    success, group_errors = self._execute_downgrade_operations(group_operations)
                else:
                    continue
                
                if success:
                    executed_operations.extend(group_operations)
                    packages_changed += len(group_operations)
                else:
                    errors.extend(group_errors)
                    
                    # For reverts, continue with other operations even if some fail
                    if not is_revert:
                        break
                        
            except Exception as e:
                error_msg = f"Failed to execute {group_type} operations: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                
                if not is_revert:
                    break
        
        # Determine overall success
        success = len(errors) == 0 or (is_revert and len(executed_operations) > 0)
        
        return SyncResult(
            success=success,
            operations_performed=executed_operations,
            errors=errors,
            warnings=warnings,
            packages_changed=packages_changed,
            duration_seconds=0  # Will be set by caller
        )
    
    def _group_operations(self, operations: List[PackageOperation]) -> Dict[str, List[PackageOperation]]:
        """Group operations by type for batch execution."""
        groups = {
            'remove': [],
            'install': [],
            'upgrade': [],
            'downgrade': []
        }
        
        for op in operations:
            if op.operation_type in groups:
                groups[op.operation_type].append(op)
        
        return groups
    
    def _execute_remove_operations(self, operations: List[PackageOperation]) -> Tuple[bool, List[str]]:
        """Execute package removal operations."""
        if not operations:
            return True, []
        
        package_names = [op.package_name for op in operations]
        logger.info(f"Removing {len(package_names)} packages: {', '.join(package_names[:5])}{'...' if len(package_names) > 5 else ''}")
        
        if self._dry_run:
            logger.info("DRY RUN: Would remove packages")
            return True, []
        
        try:
            # Use pacman -R to remove packages
            cmd = ['pacman', '-R', '--noconfirm'] + package_names
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            logger.info(f"Successfully removed {len(package_names)} packages")
            return True, []
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to remove packages: {e.stderr}"
            logger.error(error_msg)
            return False, [error_msg]
    
    def _execute_install_operations(self, operations: List[PackageOperation]) -> Tuple[bool, List[str]]:
        """Execute package installation operations."""
        if not operations:
            return True, []
        
        package_specs = []
        for op in operations:
            if op.target_version:
                package_specs.append(f"{op.package_name}={op.target_version}")
            else:
                package_specs.append(op.package_name)
        
        logger.info(f"Installing {len(package_specs)} packages: {', '.join(package_specs[:5])}{'...' if len(package_specs) > 5 else ''}")
        
        if self._dry_run:
            logger.info("DRY RUN: Would install packages")
            return True, []
        
        try:
            # Use pacman -S to install packages
            cmd = ['pacman', '-S', '--noconfirm'] + package_specs
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            logger.info(f"Successfully installed {len(package_specs)} packages")
            return True, []
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to install packages: {e.stderr}"
            logger.error(error_msg)
            return False, [error_msg]
    
    def _execute_upgrade_operations(self, operations: List[PackageOperation]) -> Tuple[bool, List[str]]:
        """Execute package upgrade operations."""
        if not operations:
            return True, []
        
        package_specs = []
        for op in operations:
            if op.target_version:
                package_specs.append(f"{op.package_name}={op.target_version}")
            else:
                package_specs.append(op.package_name)
        
        logger.info(f"Upgrading {len(package_specs)} packages: {', '.join(package_specs[:5])}{'...' if len(package_specs) > 5 else ''}")
        
        if self._dry_run:
            logger.info("DRY RUN: Would upgrade packages")
            return True, []
        
        try:
            # Use pacman -S to upgrade packages (same as install)
            cmd = ['pacman', '-S', '--noconfirm'] + package_specs
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            logger.info(f"Successfully upgraded {len(package_specs)} packages")
            return True, []
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to upgrade packages: {e.stderr}"
            logger.error(error_msg)
            return False, [error_msg]
    
    def _execute_downgrade_operations(self, operations: List[PackageOperation]) -> Tuple[bool, List[str]]:
        """Execute package downgrade operations."""
        if not operations:
            return True, []
        
        errors = []
        warnings = []
        
        # Downgrades are more complex and risky - handle individually
        for op in operations:
            try:
                success = self._downgrade_single_package(op)
                if not success:
                    error_msg = f"Failed to downgrade {op.package_name} to {op.target_version}"
                    errors.append(error_msg)
            except Exception as e:
                error_msg = f"Error downgrading {op.package_name}: {e}"
                errors.append(error_msg)
        
        if errors:
            logger.warning(f"Some downgrades failed: {len(errors)} errors")
            return False, errors
        else:
            logger.info(f"Successfully downgraded {len(operations)} packages")
            return True, []
    
    def _downgrade_single_package(self, operation: PackageOperation) -> bool:
        """
        Downgrade a single package to a specific version.
        
        This is complex because pacman doesn't directly support downgrades.
        We need to check package cache or use alternative methods.
        """
        logger.info(f"Attempting to downgrade {operation.package_name} from {operation.current_version} to {operation.target_version}")
        
        if self._dry_run:
            logger.info("DRY RUN: Would downgrade package")
            return True
        
        try:
            # First, try to find the package in cache
            cache_path = self._find_package_in_cache(operation.package_name, operation.target_version)
            
            if cache_path:
                # Install from cache
                cmd = ['pacman', '-U', '--noconfirm', cache_path]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                logger.info(f"Successfully downgraded {operation.package_name} using cached package")
                return True
            else:
                # Try to download and install specific version
                return self._download_and_install_version(operation)
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to downgrade {operation.package_name}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downgrading {operation.package_name}: {e}")
            return False
    
    def _find_package_in_cache(self, package_name: str, version: str) -> Optional[str]:
        """Find a specific package version in the pacman cache."""
        cache_dir = self.pacman.config.cache_dir
        
        # Look for package files matching the name and version
        import glob
        pattern = os.path.join(cache_dir, f"{package_name}-{version}-*.pkg.tar.*")
        matches = glob.glob(pattern)
        
        if matches:
            # Return the first match (there should typically be only one)
            return matches[0]
        
        return None
    
    def _download_and_install_version(self, operation: PackageOperation) -> bool:
        """
        Download and install a specific package version.
        
        This is a fallback when the package isn't in cache.
        Note: This is complex and may not always work depending on repository availability.
        """
        logger.warning(f"Package {operation.package_name}={operation.target_version} not found in cache")
        logger.warning("Downgrade may not be possible without cached package")
        
        # For now, we'll log this as a limitation
        # In a production system, you might want to:
        # 1. Check Arch Linux Archive (ALA) for older packages
        # 2. Use a custom repository with older versions
        # 3. Build from source with specific version
        
        return False


class StateManager:
    """
    Manages system state snapshots and history for revert operations.
    
    This class handles:
    - Storing system state snapshots
    - Retrieving previous states for revert operations
    - Managing state history and cleanup
    """
    
    def __init__(self, storage_path: str = None):
        if storage_path is None:
            import tempfile
            self.storage_path = os.path.join(tempfile.gettempdir(), "pacman_sync_states")
        else:
            self.storage_path = storage_path
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
    def save_state(self, state: SystemState, is_target: bool = False) -> str:
        """
        Save a system state snapshot.
        
        Args:
            state: SystemState to save
            is_target: Whether this is a target state (vs. backup state)
            
        Returns:
            State ID for later retrieval
        """
        state_id = f"{state.endpoint_id}_{int(state.timestamp.timestamp())}"
        filename = f"state_{state_id}.json"
        filepath = os.path.join(self.storage_path, filename)
        
        state_data = {
            'id': state_id,
            'endpoint_id': state.endpoint_id,
            'timestamp': state.timestamp.isoformat(),
            'pacman_version': state.pacman_version,
            'architecture': state.architecture,
            'is_target': is_target,
            'packages': [
                {
                    'package_name': pkg.package_name,
                    'version': pkg.version,
                    'repository': pkg.repository,
                    'installed_size': pkg.installed_size,
                    'dependencies': pkg.dependencies
                }
                for pkg in state.packages
            ]
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            logger.info(f"Saved system state {state_id} with {len(state.packages)} packages")
            return state_id
            
        except Exception as e:
            logger.error(f"Failed to save state {state_id}: {e}")
            raise
    
    def load_state(self, state_id: str) -> Optional[SystemState]:
        """
        Load a system state snapshot.
        
        Args:
            state_id: ID of the state to load
            
        Returns:
            SystemState object or None if not found
        """
        filename = f"state_{state_id}.json"
        filepath = os.path.join(self.storage_path, filename)
        
        if not os.path.exists(filepath):
            logger.warning(f"State file not found: {filepath}")
            return None
        
        try:
            with open(filepath, 'r') as f:
                state_data = json.load(f)
            
            packages = [
                PackageState(
                    package_name=pkg['package_name'],
                    version=pkg['version'],
                    repository=pkg['repository'],
                    installed_size=pkg['installed_size'],
                    dependencies=pkg.get('dependencies', [])
                )
                for pkg in state_data['packages']
            ]
            
            state = SystemState(
                endpoint_id=state_data['endpoint_id'],
                timestamp=datetime.fromisoformat(state_data['timestamp']),
                packages=packages,
                pacman_version=state_data['pacman_version'],
                architecture=state_data['architecture']
            )
            
            logger.info(f"Loaded system state {state_id} with {len(packages)} packages")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load state {state_id}: {e}")
            return None
    
    def get_previous_state(self, endpoint_id: str) -> Optional[SystemState]:
        """
        Get the most recent previous state for an endpoint.
        
        Args:
            endpoint_id: ID of the endpoint
            
        Returns:
            Most recent SystemState or None if no previous state exists
        """
        try:
            # List all state files for this endpoint
            state_files = []
            for filename in os.listdir(self.storage_path):
                if filename.startswith(f"state_{endpoint_id}_") and filename.endswith('.json'):
                    state_files.append(filename)
            
            if not state_files:
                logger.info(f"No previous states found for endpoint {endpoint_id}")
                return None
            
            # Sort by timestamp (newest first)
            state_files.sort(reverse=True)
            
            # Load the most recent state
            most_recent = state_files[0]
            state_id = most_recent.replace('state_', '').replace('.json', '')
            
            return self.load_state(state_id)
            
        except Exception as e:
            logger.error(f"Failed to get previous state for {endpoint_id}: {e}")
            return None
    
    def cleanup_old_states(self, endpoint_id: str, keep_count: int = 10):
        """
        Clean up old state files, keeping only the most recent ones.
        
        Args:
            endpoint_id: ID of the endpoint
            keep_count: Number of recent states to keep
        """
        try:
            # List all state files for this endpoint
            state_files = []
            for filename in os.listdir(self.storage_path):
                if filename.startswith(f"state_{endpoint_id}_") and filename.endswith('.json'):
                    filepath = os.path.join(self.storage_path, filename)
                    mtime = os.path.getmtime(filepath)
                    state_files.append((filename, mtime))
            
            if len(state_files) <= keep_count:
                return  # Nothing to clean up
            
            # Sort by modification time (newest first)
            state_files.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old files
            files_to_remove = state_files[keep_count:]
            for filename, _ in files_to_remove:
                filepath = os.path.join(self.storage_path, filename)
                os.remove(filepath)
                logger.info(f"Removed old state file: {filename}")
            
            logger.info(f"Cleaned up {len(files_to_remove)} old state files for {endpoint_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old states for {endpoint_id}: {e}")