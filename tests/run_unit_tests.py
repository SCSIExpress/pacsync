#!/usr/bin/env python3
"""
Comprehensive unit test runner for the Pacman Sync Utility.

This script runs all unit tests for core components including data models,
API endpoints, core services, Qt components, pacman interface, and database operations.
"""

import sys
import subprocess
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_test_suite(test_file, description):
    """Run a specific test suite and return results."""
    print(f"\n{'='*60}")
    print(f"Running {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            f"tests/{test_file}", 
            "-v", "--tb=short"
        ], capture_output=True, text=True, cwd=project_root)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {test_file}: {e}")
        return False

def main():
    """Run all unit test suites."""
    print("Pacman Sync Utility - Unit Test Suite")
    print("=====================================")
    
    test_suites = [
        ("test_models_unit.py", "Data Models Unit Tests"),
        ("test_pool_manager_unit.py", "Pool Manager Unit Tests"),
        ("test_sync_coordinator_unit.py", "Sync Coordinator Unit Tests"),
        ("test_repository_analyzer_unit.py", "Repository Analyzer Unit Tests"),
        ("test_api_endpoints_unit.py", "API Endpoints Unit Tests"),
        ("test_qt_components_unit.py", "Qt Components Unit Tests"),
        ("test_pacman_interface_unit.py", "Pacman Interface Unit Tests"),
        ("test_database_operations_unit.py", "Database Operations Unit Tests")
    ]
    
    results = {}
    total_passed = 0
    total_failed = 0
    
    for test_file, description in test_suites:
        success = run_test_suite(test_file, description)
        results[description] = success
        if success:
            total_passed += 1
        else:
            total_failed += 1
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUITE SUMMARY")
    print(f"{'='*60}")
    
    for description, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {description}")
    
    print(f"\nOverall Results:")
    print(f"  Passed: {total_passed}/{len(test_suites)}")
    print(f"  Failed: {total_failed}/{len(test_suites)}")
    
    if total_failed == 0:
        print("\n🎉 All unit tests passed successfully!")
        print("\nCore components are ready for integration testing.")
        return 0
    else:
        print(f"\n❌ {total_failed} test suite(s) failed.")
        print("Please review the failed tests and fix any issues.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)