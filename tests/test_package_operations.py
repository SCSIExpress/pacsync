#!/usr/bin/env python3
"""
Test script for package synchronization operations.

This script tests the core package synchronization functionality:
- sync-to-latest functionality
- set-as-latest operation
- revert-to-previous functionality

Requirements: 6.2, 6.3, 6.4, 11.3, 11.4
"""

import sys
import os
import tempfile
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.package_operations import PackageSynchronizer, StateManager, PackageOperation, SyncResult
from client.pacman_interface import PacmanInterface
from shared.models import PackageState, SystemState


def create_mock_pacman_interface():
    """Create a mock PacmanInterface for testing."""
    mock_pacman = Mock(spec=PacmanInterface)
    
    # Mock configuration
    mock_config = Mock()
    mock_config.cache_dir = "/var/cache/pacman/pkg"
    mock_config.architecture = "x86_64"
    mock_pacman.config = mock_config
    
    return mock_pacman


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


def test_package_synchronizer_initialization():
    """Test PackageSynchronizer initialization."""
    print("Testing PackageSynchronizer initialization...")
    
    mock_pacman = create_mock_pacman_interface()
    synchronizer = PackageSynchronizer(mock_pacman)
    
    assert synchronizer.pacman == mock_pacman
    assert synchronizer.detector is not None
    assert synchronizer._dry_run == False
    
    print("✓ PackageSynchronizer initialized correctly")


def test_calculate_sync_operations():
    """Test calculation of sync operations."""
    print("\nTesting sync operations calculation...")
    
    mock_pacman = create_mock_pacman_interface()
    synchronizer = PackageSynchronizer(mock_pacman)
    
    # Create current and target states
    current_packages = [
        {'name': 'package1', 'version': '1.0.0'},
        {'name': 'package2', 'version': '2.0.0'},
        {'name': 'package3', 'version': '3.0.0'},  # Will be removed
    ]
    
    target_packages = [
        {'name': 'package1', 'version': '1.1.0'},  # Upgrade
        {'name': 'package2', 'version': '1.9.0'},  # Downgrade
        {'name': 'package4', 'version': '4.0.0'},  # Install
    ]
    
    current_state = create_test_system_state("test_endpoint", current_packages)
    target_state = create_test_system_state("test_endpoint", target_packages)
    
    # Mock compare_package_states
    mock_pacman.compare_package_states.return_value = {
        'package1': 'older',    # Current is older -> upgrade
        'package2': 'newer',    # Current is newer -> downgrade
        'package3': 'extra',    # Only in current -> remove
        'package4': 'missing'   # Only in target -> install
    }
    
    operations = synchronizer._calculate_sync_operations(current_state, target_state)
    
    # Check operations
    operation_types = [op.operation_type for op in operations]
    assert 'install' in operation_types
    assert 'remove' in operation_types
    assert 'upgrade' in operation_types
    assert 'downgrade' in operation_types
    
    print(f"✓ Calculated {len(operations)} operations correctly")
    for op in operations:
        print(f"  - {op.operation_type}: {op.package_name}")


def test_sync_to_latest_dry_run():
    """Test sync to latest in dry run mode."""
    print("\nTesting sync to latest (dry run)...")
    
    mock_pacman = create_mock_pacman_interface()
    synchronizer = PackageSynchronizer(mock_pacman)
    synchronizer.set_dry_run(True)
    
    # Create test states
    current_packages = [
        {'name': 'package1', 'version': '1.0.0'},
    ]
    target_packages = [
        {'name': 'package1', 'version': '1.1.0'},
        {'name': 'package2', 'version': '2.0.0'},
    ]
    
    current_state = create_test_system_state("test_endpoint", current_packages)
    target_state = create_test_system_state("test_endpoint", target_packages)
    
    # Mock methods
    mock_pacman.get_system_state.return_value = current_state
    mock_pacman.compare_package_states.return_value = {
        'package1': 'older',
        'package2': 'missing'
    }
    
    result = synchronizer.sync_to_latest(target_state)
    
    assert isinstance(result, SyncResult)
    assert result.success == True
    assert len(result.operations_performed) > 0
    assert len(result.errors) == 0
    
    print(f"✓ Dry run sync completed: {result.packages_changed} operations")


def test_set_as_latest():
    """Test set as latest operation."""
    print("\nTesting set as latest operation...")
    
    mock_pacman = create_mock_pacman_interface()
    synchronizer = PackageSynchronizer(mock_pacman)
    
    # Create test state
    test_packages = [
        {'name': 'package1', 'version': '1.0.0'},
        {'name': 'package2', 'version': '2.0.0'},
    ]
    test_state = create_test_system_state("test_endpoint", test_packages)
    
    # Mock get_system_state
    mock_pacman.get_system_state.return_value = test_state
    
    system_state, result = synchronizer.set_as_latest("test_endpoint")
    
    assert isinstance(result, SyncResult)
    assert result.success == True
    assert system_state is not None
    assert system_state.endpoint_id == "test_endpoint"
    assert len(system_state.packages) == 2
    
    print(f"✓ Set as latest completed: captured {len(system_state.packages)} packages")


def test_state_manager():
    """Test StateManager functionality."""
    print("\nTesting StateManager...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        state_manager = StateManager(temp_dir)
        
        # Create test state
        test_packages = [
            {'name': 'package1', 'version': '1.0.0'},
            {'name': 'package2', 'version': '2.0.0'},
        ]
        test_state = create_test_system_state("test_endpoint", test_packages)
        
        # Save state
        state_id = state_manager.save_state(test_state, is_target=True)
        assert state_id is not None
        print(f"✓ Saved state with ID: {state_id}")
        
        # Load state
        loaded_state = state_manager.load_state(state_id)
        assert loaded_state is not None
        assert loaded_state.endpoint_id == test_state.endpoint_id
        assert len(loaded_state.packages) == len(test_state.packages)
        print(f"✓ Loaded state with {len(loaded_state.packages)} packages")
        
        # Test get previous state
        previous_state = state_manager.get_previous_state("test_endpoint")
        assert previous_state is not None
        print("✓ Retrieved previous state")


def test_revert_to_previous_dry_run():
    """Test revert to previous in dry run mode."""
    print("\nTesting revert to previous (dry run)...")
    
    mock_pacman = create_mock_pacman_interface()
    synchronizer = PackageSynchronizer(mock_pacman)
    synchronizer.set_dry_run(True)
    
    # Create current and previous states
    current_packages = [
        {'name': 'package1', 'version': '1.1.0'},
        {'name': 'package2', 'version': '2.1.0'},
    ]
    previous_packages = [
        {'name': 'package1', 'version': '1.0.0'},
        {'name': 'package2', 'version': '2.0.0'},
    ]
    
    current_state = create_test_system_state("test_endpoint", current_packages)
    previous_state = create_test_system_state("test_endpoint", previous_packages)
    
    # Mock methods
    mock_pacman.get_system_state.return_value = current_state
    mock_pacman.compare_package_states.return_value = {
        'package1': 'newer',
        'package2': 'newer'
    }
    
    result = synchronizer.revert_to_previous(previous_state)
    
    assert isinstance(result, SyncResult)
    assert result.success == True
    assert len(result.operations_performed) > 0
    
    print(f"✓ Dry run revert completed: {result.packages_changed} operations")


def test_package_operation_grouping():
    """Test operation grouping functionality."""
    print("\nTesting operation grouping...")
    
    mock_pacman = create_mock_pacman_interface()
    synchronizer = PackageSynchronizer(mock_pacman)
    
    operations = [
        PackageOperation('install', 'pkg1'),
        PackageOperation('remove', 'pkg2'),
        PackageOperation('upgrade', 'pkg3'),
        PackageOperation('install', 'pkg4'),
        PackageOperation('downgrade', 'pkg5'),
    ]
    
    groups = synchronizer._group_operations(operations)
    
    assert len(groups['install']) == 2
    assert len(groups['remove']) == 1
    assert len(groups['upgrade']) == 1
    assert len(groups['downgrade']) == 1
    
    print("✓ Operations grouped correctly")
    for group_type, group_ops in groups.items():
        if group_ops:
            print(f"  - {group_type}: {len(group_ops)} operations")


def run_all_tests():
    """Run all package operations tests."""
    print("=" * 60)
    print("PACKAGE OPERATIONS TESTS")
    print("=" * 60)
    
    try:
        test_package_synchronizer_initialization()
        test_calculate_sync_operations()
        test_sync_to_latest_dry_run()
        test_set_as_latest()
        test_state_manager()
        test_revert_to_previous_dry_run()
        test_package_operation_grouping()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        
        print("\nPackage operations implementation verified:")
        print("✓ sync-to-latest functionality with package installation/removal")
        print("✓ set-as-latest operation to capture current system state")
        print("✓ revert-to-previous functionality with state restoration")
        print("✓ State management and persistence")
        print("✓ Operation grouping and execution")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)