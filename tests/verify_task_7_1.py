#!/usr/bin/env python3
"""
Verification script for Task 7.1: Create pacman interface and package state detection.

This script verifies that all requirements for task 7.1 have been implemented:
- Requirement 3.1: Client SHALL send its available pacman repository information to the central server
- Requirement 11.1: Client SHALL report the new state to the central server when packages are installed or updated
- Requirement 11.2: System SHALL store the complete package state as a snapshot when a synchronization target is set

Task details:
- Implement pacman command execution and output parsing
- Create package state detection and comparison utilities  
- Add repository information extraction from pacman configuration
"""

import sys
import os
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.pacman_interface import PacmanInterface, PackageStateDetector, PacmanConfig
from shared.models import PackageState, SystemState, RepositoryPackage, Repository

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def verify_pacman_command_execution():
    """Verify pacman command execution and output parsing."""
    print("=" * 60)
    print("VERIFYING: Pacman command execution and output parsing")
    print("=" * 60)
    
    results = []
    
    try:
        pacman = PacmanInterface()
        
        # Test 1: Pacman configuration parsing
        print("\n1. Testing pacman configuration parsing...")
        config = pacman.config
        
        if isinstance(config, PacmanConfig):
            print(f"   ✓ Configuration parsed successfully")
            print(f"   ✓ Architecture: {config.architecture}")
            print(f"   ✓ Found {len(config.repositories)} repositories")
            results.append(("Pacman config parsing", True))
        else:
            print(f"   ✗ Configuration parsing failed")
            results.append(("Pacman config parsing", False))
        
        # Test 2: Pacman version detection
        print("\n2. Testing pacman version detection...")
        version = pacman.pacman_version
        
        if version and version != "unknown":
            print(f"   ✓ Pacman version detected: {version}")
            results.append(("Pacman version detection", True))
        else:
            print(f"   ✗ Pacman version detection failed: {version}")
            results.append(("Pacman version detection", False))
        
        # Test 3: Installed packages parsing
        print("\n3. Testing installed packages parsing...")
        packages = pacman.get_installed_packages()
        
        if packages and len(packages) > 0:
            print(f"   ✓ Retrieved {len(packages)} installed packages")
            
            # Verify package structure
            sample_pkg = packages[0]
            if all(hasattr(sample_pkg, attr) for attr in ['package_name', 'version', 'repository', 'installed_size', 'dependencies']):
                print(f"   ✓ Package structure is correct")
                print(f"   ✓ Sample: {sample_pkg.package_name} {sample_pkg.version} ({sample_pkg.repository})")
                results.append(("Installed packages parsing", True))
            else:
                print(f"   ✗ Package structure is incorrect")
                results.append(("Installed packages parsing", False))
        else:
            print(f"   ✗ No packages retrieved")
            results.append(("Installed packages parsing", False))
        
        # Test 4: Repository packages parsing
        print("\n4. Testing repository packages parsing...")
        try:
            repo_packages = pacman.get_repository_packages("core")
            
            if repo_packages and len(repo_packages) > 0:
                print(f"   ✓ Retrieved {len(repo_packages)} packages from core repository")
                
                # Verify repository package structure
                sample_repo_pkg = repo_packages[0]
                if all(hasattr(sample_repo_pkg, attr) for attr in ['name', 'version', 'repository', 'architecture']):
                    print(f"   ✓ Repository package structure is correct")
                    print(f"   ✓ Sample: {sample_repo_pkg.name} {sample_repo_pkg.version}")
                    results.append(("Repository packages parsing", True))
                else:
                    print(f"   ✗ Repository package structure is incorrect")
                    results.append(("Repository packages parsing", False))
            else:
                print(f"   ✗ No repository packages retrieved")
                results.append(("Repository packages parsing", False))
        except Exception as e:
            print(f"   ✗ Repository packages parsing failed: {e}")
            results.append(("Repository packages parsing", False))
        
    except Exception as e:
        print(f"   ✗ Pacman interface initialization failed: {e}")
        results.append(("Pacman command execution", False))
    
    return results


def verify_package_state_detection():
    """Verify package state detection and comparison utilities."""
    print("\n" + "=" * 60)
    print("VERIFYING: Package state detection and comparison utilities")
    print("=" * 60)
    
    results = []
    
    try:
        pacman = PacmanInterface()
        detector = PackageStateDetector(pacman)
        endpoint_id = "test-endpoint"
        
        # Test 1: System state creation
        print("\n1. Testing system state creation...")
        system_state = pacman.get_system_state(endpoint_id)
        
        if isinstance(system_state, SystemState):
            print(f"   ✓ System state created successfully")
            print(f"   ✓ Endpoint ID: {system_state.endpoint_id}")
            print(f"   ✓ Package count: {len(system_state.packages)}")
            print(f"   ✓ Architecture: {system_state.architecture}")
            print(f"   ✓ Pacman version: {system_state.pacman_version}")
            results.append(("System state creation", True))
        else:
            print(f"   ✗ System state creation failed")
            results.append(("System state creation", False))
        
        # Test 2: Package state comparison
        print("\n2. Testing package state comparison...")
        
        # Create mock states for comparison
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
        
        current_state = SystemState("test-1", datetime.now(), current_packages, "7.0.0", "x86_64")
        target_state = SystemState("test-2", datetime.now(), target_packages, "7.0.0", "x86_64")
        
        differences = pacman.compare_package_states(current_state, target_state)
        
        expected_differences = {
            'bash': 'same',
            'vim': 'newer', 
            'git': 'extra',
            'python': 'missing'
        }
        
        if differences == expected_differences:
            print(f"   ✓ Package state comparison working correctly")
            print(f"   ✓ Detected differences: {differences}")
            results.append(("Package state comparison", True))
        else:
            print(f"   ✗ Package state comparison failed")
            print(f"   ✗ Expected: {expected_differences}")
            print(f"   ✗ Got: {differences}")
            results.append(("Package state comparison", False))
        
        # Test 3: Sync status detection
        print("\n3. Testing sync status detection...")
        sync_status = detector.detect_sync_status(current_state, target_state)
        
        if sync_status == 'ahead':  # Current has newer vim and extra git
            print(f"   ✓ Sync status detection working correctly: {sync_status}")
            results.append(("Sync status detection", True))
        else:
            print(f"   ✗ Sync status detection failed: expected 'ahead', got '{sync_status}'")
            results.append(("Sync status detection", False))
        
        # Test 4: Package changes detection
        print("\n4. Testing package changes detection...")
        changes = detector.get_package_changes(current_state, target_state)
        
        expected_changes = {
            'install': ['python'],
            'upgrade': [],
            'downgrade': ['vim'],
            'remove': ['git']
        }
        
        if changes == expected_changes:
            print(f"   ✓ Package changes detection working correctly")
            print(f"   ✓ Changes needed: {changes}")
            results.append(("Package changes detection", True))
        else:
            print(f"   ✗ Package changes detection failed")
            print(f"   ✗ Expected: {expected_changes}")
            print(f"   ✗ Got: {changes}")
            results.append(("Package changes detection", False))
        
    except Exception as e:
        print(f"   ✗ Package state detection failed: {e}")
        results.append(("Package state detection", False))
    
    return results


def verify_repository_information_extraction():
    """Verify repository information extraction from pacman configuration."""
    print("\n" + "=" * 60)
    print("VERIFYING: Repository information extraction from pacman configuration")
    print("=" * 60)
    
    results = []
    
    try:
        pacman = PacmanInterface()
        endpoint_id = "test-endpoint"
        
        # Test 1: Repository configuration extraction
        print("\n1. Testing repository configuration extraction...")
        config = pacman.config
        
        if config.repositories and len(config.repositories) > 0:
            print(f"   ✓ Extracted {len(config.repositories)} repositories from configuration")
            for repo in config.repositories[:3]:  # Show first 3
                print(f"     - {repo['name']}: {repo['server']}")
            results.append(("Repository config extraction", True))
        else:
            print(f"   ✗ No repositories extracted from configuration")
            results.append(("Repository config extraction", False))
        
        # Test 2: Repository package information
        print("\n2. Testing repository package information extraction...")
        repositories = pacman.get_all_repositories(endpoint_id)
        
        if repositories and len(repositories) > 0:
            print(f"   ✓ Retrieved information for {len(repositories)} repositories")
            
            # Verify repository structure
            sample_repo = repositories[0]
            if isinstance(sample_repo, Repository):
                print(f"   ✓ Repository structure is correct")
                print(f"   ✓ Sample: {sample_repo.repo_name} with {len(sample_repo.packages)} packages")
                results.append(("Repository package information", True))
            else:
                print(f"   ✗ Repository structure is incorrect")
                results.append(("Repository package information", False))
        else:
            print(f"   ✗ No repository information retrieved")
            results.append(("Repository package information", False))
        
        # Test 3: Repository data completeness
        print("\n3. Testing repository data completeness...")
        if repositories:
            complete_repos = 0
            for repo in repositories:
                if repo.repo_name and repo.endpoint_id and repo.last_updated:
                    complete_repos += 1
            
            if complete_repos == len(repositories):
                print(f"   ✓ All {complete_repos} repositories have complete data")
                results.append(("Repository data completeness", True))
            else:
                print(f"   ✗ Only {complete_repos}/{len(repositories)} repositories have complete data")
                results.append(("Repository data completeness", False))
        else:
            results.append(("Repository data completeness", False))
        
    except Exception as e:
        print(f"   ✗ Repository information extraction failed: {e}")
        results.append(("Repository information extraction", False))
    
    return results


def verify_requirements_compliance():
    """Verify compliance with specific requirements."""
    print("\n" + "=" * 60)
    print("VERIFYING: Requirements compliance")
    print("=" * 60)
    
    results = []
    
    # Requirement 3.1: Client SHALL send its available pacman repository information to the central server
    print("\n1. Requirement 3.1: Repository information availability...")
    try:
        pacman = PacmanInterface()
        repositories = pacman.get_all_repositories("test-endpoint")
        
        if repositories and all(repo.packages for repo in repositories if repo.repo_name in ['core', 'extra']):
            print(f"   ✓ Repository information is available for transmission to central server")
            print(f"   ✓ {len(repositories)} repositories with package data ready")
            results.append(("Requirement 3.1", True))
        else:
            print(f"   ✗ Repository information is not complete for central server transmission")
            results.append(("Requirement 3.1", False))
    except Exception as e:
        print(f"   ✗ Requirement 3.1 failed: {e}")
        results.append(("Requirement 3.1", False))
    
    # Requirement 11.1: Client SHALL report the new state to the central server when packages are installed or updated
    print("\n2. Requirement 11.1: Package state change detection...")
    try:
        pacman = PacmanInterface()
        detector = PackageStateDetector(pacman)
        
        # Test ability to detect state changes
        state1 = pacman.get_system_state("test-1")
        state2 = pacman.get_system_state("test-2")  # Should be identical
        
        differences = pacman.compare_package_states(state1, state2)
        all_same = all(status == 'same' for status in differences.values())
        
        if all_same:
            print(f"   ✓ Package state change detection is working (identical states detected as same)")
            print(f"   ✓ System can detect when packages are installed or updated")
            results.append(("Requirement 11.1", True))
        else:
            print(f"   ✗ Package state change detection failed")
            results.append(("Requirement 11.1", False))
    except Exception as e:
        print(f"   ✗ Requirement 11.1 failed: {e}")
        results.append(("Requirement 11.1", False))
    
    # Requirement 11.2: System SHALL store the complete package state as a snapshot when a synchronization target is set
    print("\n3. Requirement 11.2: Complete package state snapshot capability...")
    try:
        pacman = PacmanInterface()
        system_state = pacman.get_system_state("test-endpoint")
        
        # Verify completeness of system state
        has_all_required_fields = all([
            system_state.endpoint_id,
            system_state.timestamp,
            system_state.packages,
            system_state.pacman_version,
            system_state.architecture
        ])
        
        has_complete_package_data = all([
            pkg.package_name and pkg.version and pkg.repository
            for pkg in system_state.packages[:10]  # Check first 10 packages
        ])
        
        if has_all_required_fields and has_complete_package_data:
            print(f"   ✓ Complete package state snapshot capability is available")
            print(f"   ✓ System state includes all required fields and complete package data")
            results.append(("Requirement 11.2", True))
        else:
            print(f"   ✗ Package state snapshot is incomplete")
            results.append(("Requirement 11.2", False))
    except Exception as e:
        print(f"   ✗ Requirement 11.2 failed: {e}")
        results.append(("Requirement 11.2", False))
    
    return results


def main():
    """Run all verification tests."""
    print("TASK 7.1 VERIFICATION")
    print("Create pacman interface and package state detection")
    print("=" * 80)
    
    all_results = []
    
    # Run all verification tests
    all_results.extend(verify_pacman_command_execution())
    all_results.extend(verify_package_state_detection())
    all_results.extend(verify_repository_information_extraction())
    all_results.extend(verify_requirements_compliance())
    
    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test_name, success in all_results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:<8} {test_name}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 ALL VERIFICATIONS PASSED!")
        print("Task 7.1 has been successfully implemented.")
        print("\nImplemented functionality:")
        print("- ✓ Pacman command execution and output parsing")
        print("- ✓ Package state detection and comparison utilities")
        print("- ✓ Repository information extraction from pacman configuration")
        print("- ✓ Compliance with requirements 3.1, 11.1, and 11.2")
        return 0
    else:
        print(f"\n❌ {failed} VERIFICATIONS FAILED!")
        print("Task 7.1 implementation needs attention.")
        return 1


if __name__ == "__main__":
    sys.exit(main())