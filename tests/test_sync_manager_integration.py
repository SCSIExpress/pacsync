#!/usr/bin/env python3
"""
Integration test for sync manager with package operations.

This script tests the integration between SyncManager and package operations:
- sync-to-latest through sync manager
- set-as-latest through sync manager  
- revert-to-previous through sync manager

Requirements: 6.2, 6.3, 6.4, 11.3, 11.4
"""

import sys
import os
import tempfile
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.sync_manager import SyncManager
from client.config import ClientConfiguration
from client.qt.application import SyncStatus
from shared.models import PackageState, SystemState


def create_mock_config():
    """Create a mock ClientConfiguration."""
    mock_config = Mock(spec=ClientConfiguration)
    mock_config.get_server_url.return_value = "http://localhost:8080"
    mock_config.get_server_timeout.return_value = 30
    mock_config.get_retry_attempts.return_value = 3
    mock_config.get_retry_delay.return_value = 1.0
    mock_config.get_update_interval.return_value = 300
    mock_config.get_endpoint_name.return_value = "test_endpoint"
    return mock_config


def create_test_system_state(endpoint_id: str, packages_data: list) -> SystemState:
    """Create a test SystemState with given packages."""
    packages = []
    for pkg_data in packages_data:
        packages.append(PackageState(
            package_name=pkg_data['name'],
            version=pkg_data['version'],
            repository=pkg_data.get('repository', 'core'),
            installed_size=pkg_data.get('size', 1024),
            dependencies=pkg_data.get('dependencies', [])
        ))
    
    return SystemState(
        endpoint_id=endpoint_id,
        timestamp=datetime.now(),
        packages=packages,
        pacman_version="6.0.1",
        architecture="x86_64"
    )


def test_sync_manager_initialization():
    """Test SyncManager initialization with package operations."""
    print("Testing SyncManager initialization...")
    
    mock_config = create_mock_config()
    
    with patch('client.sync_manager.PacmanInterface') as mock_pacman_class:
        with patch('client.sync_manager.PackageSynchronizer') as mock_sync_class:
            with patch('client.sync_manager.StateManager') as mock_state_class:
                sync_manager = SyncManager(mock_config)
                
                # Verify components were initialized
                assert mock_pacman_class.called
                assert mock_sync_class.called
                assert mock_state_class.called
                
                print("✓ SyncManager initialized with package operations")


def test_set_as_latest_operation():
    """Test set as latest operation through sync manager."""
    print("\nTesting set as latest operation...")
    
    mock_config = create_mock_config()
    
    with patch('client.sync_manager.PacmanInterface') as mock_pacman_class:
        with patch('client.sync_manager.PackageSynchronizer') as mock_sync_class:
            with patch('client.sync_manager.StateManager') as mock_state_class:
                
                # Setup mocks
                mock_pacman = Mock()
                mock_pacman_class.return_value = mock_pacman
                
                mock_synchronizer = Mock()
                mock_sync_class.return_value = mock_synchronizer
                
                mock_state_manager = Mock()
                mock_state_class.return_value = mock_state_manager
                
                # Create test state
                test_packages = [
                    {'name': 'package1', 'version': '1.0.0'},
                    {'name': 'package2', 'version': '2.0.0'},
                ]
                test_state = create_test_system_state("test_endpoint", test_packages)
                
                mock_pacman.get_system_state.return_value = test_state
                
                sync_manager = SyncManager(mock_config)
                sync_manager._is_authenticated = True
                sync_manager._endpoint_id = "test_endpoint"
                
                # Call set_as_latest
                sync_manager.set_as_latest()
                
                # Verify pacman interface was called to save current state
                mock_pacman.get_system_state.assert_called_with("test_endpoint")
                mock_state_manager.save_state.assert_called()
                
                print("✓ Set as latest operation queued correctly")


def test_sync_to_latest_with_target_state():
    """Test sync to latest with provided target state."""
    print("\nTesting sync to latest with target state...")
    
    mock_config = create_mock_config()
    
    with patch('client.sync_manager.PacmanInterface') as mock_pacman_class:
        with patch('client.sync_manager.PackageSynchronizer') as mock_sync_class:
            with patch('client.sync_manager.StateManager') as mock_state_class:
                
                sync_manager = SyncManager(mock_config)
                sync_manager._is_authenticated = True
                sync_manager._endpoint_id = "test_endpoint"
                
                # Create target state
                target_packages = [
                    {'name': 'package1', 'version': '1.1.0'},
                    {'name': 'package2', 'version': '2.1.0'},
                ]
                target_state = create_test_system_state("test_endpoint", target_packages)
                
                # Call sync_to_latest with target state
                sync_manager.sync_to_latest(target_state)
                
                # Verify status was updated to syncing
                assert sync_manager.get_current_status() == SyncStatus.SYNCING
                
                print("✓ Sync to latest with target state queued correctly")


def test_revert_to_previous_operation():
    """Test revert to previous operation through sync manager."""
    print("\nTesting revert to previous operation...")
    
    mock_config = create_mock_config()
    
    with patch('client.sync_manager.PacmanInterface') as mock_pacman_class:
        with patch('client.sync_manager.PackageSynchronizer') as mock_sync_class:
            with patch('client.sync_manager.StateManager') as mock_state_class:
                
                # Setup mocks
                mock_pacman = Mock()
                mock_pacman_class.return_value = mock_pacman
                
                mock_state_manager = Mock()
                mock_state_class.return_value = mock_state_manager
                
                # Create current state
                current_packages = [
                    {'name': 'package1', 'version': '1.1.0'},
                    {'name': 'package2', 'version': '2.1.0'},
                ]
                current_state = create_test_system_state("test_endpoint", current_packages)
                
                mock_pacman.get_system_state.return_value = current_state
                
                sync_manager = SyncManager(mock_config)
                sync_manager._is_authenticated = True
                sync_manager._endpoint_id = "test_endpoint"
                
                # Call revert_to_previous
                sync_manager.revert_to_previous()
                
                # Verify current state was saved before revert
                mock_pacman.get_system_state.assert_called_with("test_endpoint")
                mock_state_manager.save_state.assert_called()
                
                print("✓ Revert to previous operation queued correctly")


def test_authentication_required():
    """Test that operations require authentication."""
    print("\nTesting authentication requirements...")
    
    mock_config = create_mock_config()
    
    with patch('client.sync_manager.PacmanInterface'):
        with patch('client.sync_manager.PackageSynchronizer'):
            with patch('client.sync_manager.StateManager'):
                
                sync_manager = SyncManager(mock_config)
                # Don't set authentication
                
                # Track error signals
                error_messages = []
                sync_manager.error_occurred.connect(lambda msg: error_messages.append(msg))
                
                # Try operations without authentication
                sync_manager.sync_to_latest()
                sync_manager.set_as_latest()
                sync_manager.revert_to_previous()
                
                # Should have received error messages
                assert len(error_messages) == 3
                for msg in error_messages:
                    assert "Not authenticated" in msg
                
                print("✓ Operations correctly require authentication")


def test_status_management():
    """Test status management during operations."""
    print("\nTesting status management...")
    
    mock_config = create_mock_config()
    
    with patch('client.sync_manager.PacmanInterface'):
        with patch('client.sync_manager.PackageSynchronizer'):
            with patch('client.sync_manager.StateManager'):
                
                sync_manager = SyncManager(mock_config)
                sync_manager._is_authenticated = True
                sync_manager._endpoint_id = "test_endpoint"
                
                # Track status changes
                status_changes = []
                sync_manager.status_changed.connect(lambda status: status_changes.append(status))
                
                # Initial status should be OFFLINE
                assert sync_manager.get_current_status() == SyncStatus.OFFLINE
                
                # Create target state and sync
                target_packages = [{'name': 'package1', 'version': '1.0.0'}]
                target_state = create_test_system_state("test_endpoint", target_packages)
                
                sync_manager.sync_to_latest(target_state)
                
                # Status should change to SYNCING
                assert sync_manager.get_current_status() == SyncStatus.SYNCING
                
                print("✓ Status management works correctly")


def run_all_tests():
    """Run all sync manager integration tests."""
    print("=" * 60)
    print("SYNC MANAGER INTEGRATION TESTS")
    print("=" * 60)
    
    try:
        test_sync_manager_initialization()
        test_set_as_latest_operation()
        test_sync_to_latest_with_target_state()
        test_revert_to_previous_operation()
        test_authentication_required()
        test_status_management()
        
        print("\n" + "=" * 60)
        print("✓ ALL INTEGRATION TESTS PASSED")
        print("=" * 60)
        
        print("\nSync manager integration verified:")
        print("✓ Package operations integrated with sync manager")
        print("✓ Authentication requirements enforced")
        print("✓ Status management during operations")
        print("✓ State saving before operations")
        print("✓ Operation queueing and execution")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)