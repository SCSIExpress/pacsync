#!/usr/bin/env python3
"""
Test script for pacman interface functionality.

This script tests the pacman interface implementation to ensure it can:
1. Parse pacman configuration
2. Get installed packages
3. Get repository information
4. Compare package states
"""

import sys
import os
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.pacman_interface import PacmanInterface, PackageStateDetector
from shared.models import SystemState, PackageState

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_pacman_config():
    """Test pacman configuration parsing."""
    print("=" * 50)
    print("Testing Pacman Configuration Parsing")
    print("=" * 50)
    
    try:
        pacman = PacmanInterface()
        config = pacman.config
        
        print(f"Architecture: {config.architecture}")
        print(f"Cache Directory: {config.cache_dir}")
        print(f"Database Path: {config.db_path}")
        print(f"Log File: {config.log_file}")
        print(f"Pacman Version: {pacman.pacman_version}")
        print(f"Repositories ({len(config.repositories)}):")
        
        for repo in config.repositories:
            print(f"  - {repo['name']}: {repo['server']}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to parse pacman configuration: {e}")
        return False


def test_installed_packages():
    """Test getting installed packages."""
    print("\n" + "=" * 50)
    print("Testing Installed Package Detection")
    print("=" * 50)
    
    try:
        pacman = PacmanInterface()
        packages = pacman.get_installed_packages()
        
        print(f"Found {len(packages)} installed packages")
        
        # Show first 5 packages as examples
        print("\nFirst 5 packages:")
        for i, pkg in enumerate(packages[:5]):
            print(f"  {i+1}. {pkg.package_name} {pkg.version} ({pkg.repository})")
            print(f"     Size: {pkg.installed_size} bytes")
            print(f"     Dependencies: {len(pkg.dependencies)} packages")
        
        # Test specific package details
        if packages:
            test_pkg = packages[0]
            print(f"\nDetailed info for {test_pkg.package_name}:")
            print(f"  Version: {test_pkg.version}")
            print(f"  Repository: {test_pkg.repository}")
            print(f"  Size: {test_pkg.installed_size} bytes")
            print(f"  Dependencies: {test_pkg.dependencies[:5]}...")  # Show first 5 deps
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to get installed packages: {e}")
        return False


def test_system_state():
    """Test getting complete system state."""
    print("\n" + "=" * 50)
    print("Testing System State Detection")
    print("=" * 50)
    
    try:
        pacman = PacmanInterface()
        endpoint_id = "test-endpoint-001"
        
        system_state = pacman.get_system_state(endpoint_id)
        
        print(f"Endpoint ID: {system_state.endpoint_id}")
        print(f"Timestamp: {system_state.timestamp}")
        print(f"Pacman Version: {system_state.pacman_version}")
        print(f"Architecture: {system_state.architecture}")
        print(f"Total Packages: {len(system_state.packages)}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to get system state: {e}")
        return False


def test_repository_packages():
    """Test getting repository package information."""
    print("\n" + "=" * 50)
    print("Testing Repository Package Detection")
    print("=" * 50)
    
    try:
        pacman = PacmanInterface()
        
        # Test with core repository (should exist on most systems)
        repo_name = "core"
        packages = pacman.get_repository_packages(repo_name)
        
        print(f"Found {len(packages)} packages in {repo_name} repository")
        
        # Show first 5 packages
        print(f"\nFirst 5 packages from {repo_name}:")
        for i, pkg in enumerate(packages[:5]):
            print(f"  {i+1}. {pkg.name} {pkg.version} ({pkg.repository})")
            if pkg.description:
                print(f"     Description: {pkg.description[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to get repository packages: {e}")
        return False


def test_all_repositories():
    """Test getting all repository information."""
    print("\n" + "=" * 50)
    print("Testing All Repository Information")
    print("=" * 50)
    
    try:
        pacman = PacmanInterface()
        endpoint_id = "test-endpoint-001"
        
        repositories = pacman.get_all_repositories(endpoint_id)
        
        print(f"Found {len(repositories)} repositories")
        
        for repo in repositories:
            print(f"\nRepository: {repo.repo_name}")
            print(f"  URL: {repo.repo_url}")
            print(f"  Packages: {len(repo.packages)}")
            print(f"  Last Updated: {repo.last_updated}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to get repository information: {e}")
        return False


def test_package_comparison():
    """Test package state comparison functionality."""
    print("\n" + "=" * 50)
    print("Testing Package State Comparison")
    print("=" * 50)
    
    try:
        pacman = PacmanInterface()
        detector = PackageStateDetector(pacman)
        
        # Create mock system states for testing
        current_packages = [
            PackageState("bash", "5.1.016-1", "core", 1024000, ["glibc"]),
            PackageState("vim", "8.2.3458-1", "extra", 2048000, ["glibc"]),
            PackageState("git", "2.33.0-1", "extra", 4096000, ["curl"])
        ]
        
        target_packages = [
            PackageState("bash", "5.1.016-1", "core", 1024000, ["glibc"]),  # same
            PackageState("vim", "8.2.3400-1", "extra", 2048000, ["glibc"]),  # current newer
            PackageState("python", "3.9.7-1", "extra", 8192000, ["glibc"])  # missing in current
        ]
        
        current_state = SystemState("test-1", datetime.now(), current_packages, "6.0.1", "x86_64")
        target_state = SystemState("test-2", datetime.now(), target_packages, "6.0.1", "x86_64")
        
        # Test comparison
        differences = pacman.compare_package_states(current_state, target_state)
        print("Package differences:")
        for pkg, status in differences.items():
            print(f"  {pkg}: {status}")
        
        # Test sync status detection
        sync_status = detector.detect_sync_status(current_state, target_state)
        print(f"\nSync Status: {sync_status}")
        
        # Test package changes
        changes = detector.get_package_changes(current_state, target_state)
        print(f"\nRequired changes:")
        for action, packages in changes.items():
            if packages:
                print(f"  {action}: {packages}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to test package comparison: {e}")
        return False


def main():
    """Run all tests."""
    print("Pacman Interface Test Suite")
    print("=" * 50)
    
    tests = [
        ("Pacman Configuration", test_pacman_config),
        ("Installed Packages", test_installed_packages),
        ("System State", test_system_state),
        ("Repository Packages", test_repository_packages),
        ("All Repositories", test_all_repositories),
        ("Package Comparison", test_package_comparison)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"CRITICAL ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())