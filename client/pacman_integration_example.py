#!/usr/bin/env python3
"""
Example integration of PacmanInterface with SyncManager.

This demonstrates how the pacman interface would be integrated into the
existing client architecture to provide package state detection and
repository information submission.
"""

import sys
import os
import logging
from datetime import datetime
from typing import Optional

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.pacman_interface import PacmanInterface, PackageStateDetector
from client.config import ClientConfiguration
from shared.models import SyncStatus

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PacmanSyncIntegration:
    """
    Integration class that combines PacmanInterface with sync operations.
    
    This class would be used by the SyncManager to provide pacman-specific
    functionality for package state detection and repository analysis.
    """
    
    def __init__(self, config: ClientConfiguration):
        self.config = config
        self.pacman = PacmanInterface()
        self.detector = PackageStateDetector(self.pacman)
        self._last_system_state = None
        self._target_state = None
        
        logger.info("Pacman sync integration initialized")
    
    def get_current_system_state(self, endpoint_id: str):
        """
        Get current system state and cache it for comparison.
        
        This would be called periodically by the SyncManager to detect
        changes in package state.
        """
        try:
            system_state = self.pacman.get_system_state(endpoint_id)
            self._last_system_state = system_state
            
            logger.info(f"Retrieved system state: {len(system_state.packages)} packages")
            return system_state
            
        except Exception as e:
            logger.error(f"Failed to get system state: {e}")
            raise
    
    def get_repository_information(self, endpoint_id: str):
        """
        Get repository information for submission to central server.
        
        This implements requirement 3.1: client SHALL send its available
        pacman repository information to the central server.
        """
        try:
            repositories = self.pacman.get_all_repositories(endpoint_id)
            
            logger.info(f"Retrieved repository information for {len(repositories)} repositories")
            
            # Log summary of repository data
            for repo in repositories:
                logger.info(f"  {repo.repo_name}: {len(repo.packages)} packages")
            
            return repositories
            
        except Exception as e:
            logger.error(f"Failed to get repository information: {e}")
            raise
    
    def detect_sync_status(self, target_state: Optional[dict] = None) -> SyncStatus:
        """
        Detect current synchronization status by comparing with target state.
        
        This implements requirement 11.1: client SHALL report the new state
        to the central server when packages are installed or updated.
        """
        if not self._last_system_state:
            logger.warning("No cached system state available for comparison")
            return SyncStatus.OFFLINE
        
        if not target_state:
            logger.info("No target state available, status unknown")
            return SyncStatus.OFFLINE
        
        try:
            # Convert target state dict to SystemState object (simplified)
            # In real implementation, this would come from the server
            target_system_state = self._convert_target_state(target_state)
            
            status_str = self.detector.detect_sync_status(
                self._last_system_state, 
                target_system_state
            )
            
            # Convert string status to SyncStatus enum
            status_mapping = {
                'in_sync': SyncStatus.IN_SYNC,
                'ahead': SyncStatus.AHEAD,
                'behind': SyncStatus.BEHIND,
                'unknown': SyncStatus.OFFLINE
            }
            
            sync_status = status_mapping.get(status_str, SyncStatus.OFFLINE)
            logger.info(f"Detected sync status: {sync_status.value}")
            
            return sync_status
            
        except Exception as e:
            logger.error(f"Failed to detect sync status: {e}")
            return SyncStatus.OFFLINE
    
    def get_package_changes_needed(self, target_state: dict) -> dict:
        """
        Get detailed information about what package changes are needed
        to reach the target state.
        
        This would be used by sync operations to determine what actions
        to take during synchronization.
        """
        if not self._last_system_state:
            raise ValueError("No current system state available")
        
        try:
            target_system_state = self._convert_target_state(target_state)
            changes = self.detector.get_package_changes(
                self._last_system_state,
                target_system_state
            )
            
            logger.info("Package changes needed:")
            for action, packages in changes.items():
                if packages:
                    logger.info(f"  {action}: {len(packages)} packages")
            
            return changes
            
        except Exception as e:
            logger.error(f"Failed to get package changes: {e}")
            raise
    
    def has_package_state_changed(self, endpoint_id: str) -> bool:
        """
        Check if package state has changed since last check.
        
        This implements requirement 11.1: detect when packages are
        installed or updated and report to central server.
        """
        try:
            current_state = self.pacman.get_system_state(endpoint_id)
            
            if not self._last_system_state:
                self._last_system_state = current_state
                return True  # First time, consider it changed
            
            # Compare package lists
            current_packages = {pkg.package_name: pkg.version for pkg in current_state.packages}
            last_packages = {pkg.package_name: pkg.version for pkg in self._last_system_state.packages}
            
            # Check for differences
            changed = current_packages != last_packages
            
            if changed:
                logger.info("Package state has changed")
                self._last_system_state = current_state
            
            return changed
            
        except Exception as e:
            logger.error(f"Failed to check package state changes: {e}")
            return False
    
    def _convert_target_state(self, target_state: dict):
        """
        Convert target state dictionary to SystemState object.
        
        In a real implementation, this would handle the conversion from
        the server's target state format to our internal SystemState format.
        """
        # This is a simplified implementation for demonstration
        # Real implementation would parse the server's target state format
        from shared.models import SystemState, PackageState
        
        packages = []
        for pkg_data in target_state.get('packages', []):
            package = PackageState(
                package_name=pkg_data['name'],
                version=pkg_data['version'],
                repository=pkg_data.get('repository', 'unknown'),
                installed_size=pkg_data.get('size', 0),
                dependencies=pkg_data.get('dependencies', [])
            )
            packages.append(package)
        
        return SystemState(
            endpoint_id=target_state.get('endpoint_id', 'target'),
            timestamp=datetime.now(),
            packages=packages,
            pacman_version=target_state.get('pacman_version', 'unknown'),
            architecture=target_state.get('architecture', 'x86_64')
        )


def demo_integration():
    """Demonstrate the integration functionality."""
    print("=" * 60)
    print("Pacman Sync Integration Demo")
    print("=" * 60)
    
    # Initialize configuration (mock)
    class MockConfig:
        def get_endpoint_name(self):
            return "demo-endpoint"
    
    config = MockConfig()
    integration = PacmanSyncIntegration(config)
    endpoint_id = "demo-endpoint-001"
    
    # 1. Get current system state
    print("\n1. Getting current system state...")
    try:
        system_state = integration.get_current_system_state(endpoint_id)
        print(f"   ✓ Retrieved state with {len(system_state.packages)} packages")
        print(f"   ✓ Architecture: {system_state.architecture}")
        print(f"   ✓ Pacman version: {system_state.pacman_version}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return
    
    # 2. Get repository information
    print("\n2. Getting repository information...")
    try:
        repositories = integration.get_repository_information(endpoint_id)
        print(f"   ✓ Retrieved {len(repositories)} repositories")
        for repo in repositories[:3]:  # Show first 3
            print(f"     - {repo.repo_name}: {len(repo.packages)} packages")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return
    
    # 3. Check for package state changes
    print("\n3. Checking for package state changes...")
    try:
        changed = integration.has_package_state_changed(endpoint_id)
        print(f"   ✓ Package state changed: {changed}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # 4. Detect sync status (with mock target state)
    print("\n4. Detecting sync status...")
    try:
        # Create a mock target state for demonstration
        mock_target = {
            'endpoint_id': 'target',
            'packages': [
                {'name': 'bash', 'version': '5.1.016-1', 'repository': 'core'},
                {'name': 'vim', 'version': '8.2.3458-1', 'repository': 'extra'},
            ],
            'architecture': 'x86_64',
            'pacman_version': '7.0.0'
        }
        
        status = integration.detect_sync_status(mock_target)
        print(f"   ✓ Sync status: {status.value}")
        
        # Get detailed changes
        changes = integration.get_package_changes_needed(mock_target)
        print("   ✓ Package changes needed:")
        for action, packages in changes.items():
            if packages:
                print(f"     {action}: {len(packages)} packages")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    print("\n" + "=" * 60)
    print("Integration demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    demo_integration()