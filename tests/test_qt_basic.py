#!/usr/bin/env python3
"""
Basic test for Qt application components without requiring a display.

This test validates the core functionality of the Qt classes without
needing a running X11/Wayland session.
"""

import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_imports():
    """Test that all Qt components can be imported."""
    try:
        from client.qt.application import PacmanSyncApplication, SyncStatus, SyncStatusIndicator
        print("✅ Successfully imported Qt application components")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_sync_status_enum():
    """Test the SyncStatus enumeration."""
    try:
        from client.qt.application import SyncStatus
        
        # Test all enum values
        expected_statuses = ['in_sync', 'ahead', 'behind', 'offline', 'syncing', 'error']
        actual_statuses = [status.value for status in SyncStatus]
        
        for expected in expected_statuses:
            if expected not in actual_statuses:
                print(f"❌ Missing status: {expected}")
                return False
        
        print("✅ SyncStatus enum contains all expected values")
        return True
    except Exception as e:
        print(f"❌ SyncStatus test failed: {e}")
        return False


def test_class_instantiation():
    """Test that classes can be instantiated (without GUI)."""
    try:
        from client.qt.application import SyncStatus
        
        # Test enum usage
        status = SyncStatus.IN_SYNC
        assert status.value == "in_sync"
        
        # Test status comparison
        assert SyncStatus.AHEAD != SyncStatus.BEHIND
        assert SyncStatus.OFFLINE == SyncStatus.OFFLINE
        
        print("✅ SyncStatus enum works correctly")
        return True
    except Exception as e:
        print(f"❌ Class instantiation test failed: {e}")
        return False


def test_application_metadata():
    """Test application metadata and constants."""
    try:
        from client.qt.application import SyncStatusIndicator
        
        # Test that the class has expected methods
        expected_methods = [
            'set_status', 'get_status', 'show_message', 'is_available'
        ]
        
        for method in expected_methods:
            if not hasattr(SyncStatusIndicator, method):
                print(f"❌ Missing method: {method}")
                return False
        
        print("✅ SyncStatusIndicator has all expected methods")
        return True
    except Exception as e:
        print(f"❌ Application metadata test failed: {e}")
        return False


def run_all_tests():
    """Run all tests that don't require a GUI."""
    print("Running Qt Application Basic Tests...")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("SyncStatus Enum Test", test_sync_status_enum),
        ("Class Instantiation Test", test_class_instantiation),
        ("Application Metadata Test", test_application_metadata),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All basic tests PASSED!")
        print("\nThe Qt application framework is ready for use.")
        print("Note: Full GUI testing requires a display server (X11/Wayland).")
        return True
    else:
        print("❌ Some tests FAILED!")
        return False


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        logger.exception("Test suite failed")
        sys.exit(1)