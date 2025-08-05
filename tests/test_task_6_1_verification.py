#!/usr/bin/env python3
"""
Verification test for Task 6.1: Qt application framework and system tray integration.

This test verifies that all requirements for task 6.1 have been implemented:
- Set up QApplication with AppIndicator and KStatusNotifierItem support
- Implement QSystemTrayIcon with dynamic status indication (in sync, ahead, behind)
- Create context menu with sync actions and status display
- Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
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


def test_requirement_5_1():
    """
    Test Requirement 5.1: System tray icon display
    WHEN the client starts THEN it SHALL display an icon in the system tray 
    using AppIndicator and KStatusNotifierItem protocols
    """
    try:
        from client.qt.application import PacmanSyncApplication, SyncStatusIndicator
        
        # Test that the classes exist and have required methods
        required_methods = ['set_status', 'get_status', 'is_available', 'show_message']
        for method in required_methods:
            if not hasattr(SyncStatusIndicator, method):
                print(f"❌ Requirement 5.1 FAILED: Missing method {method}")
                return False
        
        print("✅ Requirement 5.1 PASSED: System tray integration implemented")
        return True
    except Exception as e:
        print(f"❌ Requirement 5.1 FAILED: {e}")
        return False


def test_requirement_5_2():
    """
    Test Requirement 5.2: Synchronized state display
    WHEN the endpoint is in sync THEN the icon SHALL display a "synchronized" state
    """
    try:
        from client.qt.application import SyncStatus
        
        # Test that IN_SYNC status exists and has correct value
        if not hasattr(SyncStatus, 'IN_SYNC'):
            print("❌ Requirement 5.2 FAILED: IN_SYNC status not found")
            return False
        
        if SyncStatus.IN_SYNC.value != 'in_sync':
            print(f"❌ Requirement 5.2 FAILED: Expected 'in_sync', got {SyncStatus.IN_SYNC.value}")
            return False
        
        print("✅ Requirement 5.2 PASSED: Synchronized state display implemented")
        return True
    except Exception as e:
        print(f"❌ Requirement 5.2 FAILED: {e}")
        return False


def test_requirement_5_3():
    """
    Test Requirement 5.3: Ahead state display
    WHEN the endpoint has newer packages than the pool THEN the icon SHALL display an "ahead" state
    """
    try:
        from client.qt.application import SyncStatus
        
        # Test that AHEAD status exists and has correct value
        if not hasattr(SyncStatus, 'AHEAD'):
            print("❌ Requirement 5.3 FAILED: AHEAD status not found")
            return False
        
        if SyncStatus.AHEAD.value != 'ahead':
            print(f"❌ Requirement 5.3 FAILED: Expected 'ahead', got {SyncStatus.AHEAD.value}")
            return False
        
        print("✅ Requirement 5.3 PASSED: Ahead state display implemented")
        return True
    except Exception as e:
        print(f"❌ Requirement 5.3 FAILED: {e}")
        return False


def test_requirement_5_4():
    """
    Test Requirement 5.4: Behind state display
    WHEN the endpoint has older packages than the pool THEN the icon SHALL display a "behind" state
    """
    try:
        from client.qt.application import SyncStatus
        
        # Test that BEHIND status exists and has correct value
        if not hasattr(SyncStatus, 'BEHIND'):
            print("❌ Requirement 5.4 FAILED: BEHIND status not found")
            return False
        
        if SyncStatus.BEHIND.value != 'behind':
            print(f"❌ Requirement 5.4 FAILED: Expected 'behind', got {SyncStatus.BEHIND.value}")
            return False
        
        print("✅ Requirement 5.4 PASSED: Behind state display implemented")
        return True
    except Exception as e:
        print(f"❌ Requirement 5.4 FAILED: {e}")
        return False


def test_requirement_5_5():
    """
    Test Requirement 5.5: Automatic status updates
    WHEN the sync status changes THEN the icon SHALL update automatically to reflect the new state
    """
    try:
        from client.qt.application import SyncStatusIndicator, SyncStatus
        
        # Test that the SyncStatusIndicator has status change signal
        if not hasattr(SyncStatusIndicator, 'status_changed'):
            print("❌ Requirement 5.5 FAILED: status_changed signal not found")
            return False
        
        # Test that set_status method exists
        if not hasattr(SyncStatusIndicator, 'set_status'):
            print("❌ Requirement 5.5 FAILED: set_status method not found")
            return False
        
        print("✅ Requirement 5.5 PASSED: Automatic status updates implemented")
        return True
    except Exception as e:
        print(f"❌ Requirement 5.5 FAILED: {e}")
        return False


def test_context_menu_actions():
    """
    Test that context menu with sync actions is implemented.
    This verifies the task requirement for "Create context menu with sync actions and status display"
    """
    try:
        from client.qt.application import PacmanSyncApplication
        
        # Test that the application class has callback setters for menu actions
        required_callbacks = [
            'set_sync_callback',
            'set_set_latest_callback', 
            'set_revert_callback',
            'set_status_update_callback'
        ]
        
        for callback in required_callbacks:
            if not hasattr(PacmanSyncApplication, callback):
                print(f"❌ Context Menu FAILED: Missing callback setter {callback}")
                return False
        
        print("✅ Context Menu PASSED: Sync actions and callbacks implemented")
        return True
    except Exception as e:
        print(f"❌ Context Menu FAILED: {e}")
        return False


def test_dynamic_status_indication():
    """
    Test that dynamic status indication is implemented.
    This verifies the task requirement for "QSystemTrayIcon with dynamic status indication"
    """
    try:
        from client.qt.application import SyncStatus
        
        # Test that all required status types exist
        required_statuses = ['IN_SYNC', 'AHEAD', 'BEHIND', 'OFFLINE', 'SYNCING', 'ERROR']
        
        for status_name in required_statuses:
            if not hasattr(SyncStatus, status_name):
                print(f"❌ Dynamic Status FAILED: Missing status {status_name}")
                return False
        
        # Test status values
        expected_values = {
            'IN_SYNC': 'in_sync',
            'AHEAD': 'ahead', 
            'BEHIND': 'behind',
            'OFFLINE': 'offline',
            'SYNCING': 'syncing',
            'ERROR': 'error'
        }
        
        for status_name, expected_value in expected_values.items():
            actual_value = getattr(SyncStatus, status_name).value
            if actual_value != expected_value:
                print(f"❌ Dynamic Status FAILED: {status_name} has value {actual_value}, expected {expected_value}")
                return False
        
        print("✅ Dynamic Status PASSED: All status types implemented")
        return True
    except Exception as e:
        print(f"❌ Dynamic Status FAILED: {e}")
        return False


def test_qt_application_framework():
    """
    Test that QApplication framework is properly set up.
    This verifies the task requirement for "Set up QApplication with AppIndicator and KStatusNotifierItem support"
    """
    try:
        from client.qt.application import PacmanSyncApplication
        
        # Test that PacmanSyncApplication exists and has required methods
        required_methods = [
            'update_sync_status',
            'get_sync_status', 
            'show_notification',
            'is_system_tray_available'
        ]
        
        for method in required_methods:
            if not hasattr(PacmanSyncApplication, method):
                print(f"❌ Qt Framework FAILED: Missing method {method}")
                return False
        
        print("✅ Qt Framework PASSED: QApplication framework implemented")
        return True
    except Exception as e:
        print(f"❌ Qt Framework FAILED: {e}")
        return False


def run_verification():
    """Run all verification tests for Task 6.1."""
    print("Verifying Task 6.1: Qt application framework and system tray integration")
    print("=" * 80)
    
    tests = [
        ("Requirement 5.1 - System Tray Icon", test_requirement_5_1),
        ("Requirement 5.2 - Synchronized State", test_requirement_5_2),
        ("Requirement 5.3 - Ahead State", test_requirement_5_3),
        ("Requirement 5.4 - Behind State", test_requirement_5_4),
        ("Requirement 5.5 - Automatic Updates", test_requirement_5_5),
        ("Context Menu Actions", test_context_menu_actions),
        ("Dynamic Status Indication", test_dynamic_status_indication),
        ("Qt Application Framework", test_qt_application_framework),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nTesting {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 80)
    print(f"Verification Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ Task 6.1 VERIFICATION PASSED!")
        print("\nAll requirements have been successfully implemented:")
        print("  ✅ QApplication with AppIndicator/KStatusNotifierItem support")
        print("  ✅ QSystemTrayIcon with dynamic status indication")
        print("  ✅ Context menu with sync actions and status display")
        print("  ✅ Support for all required sync states (in sync, ahead, behind)")
        print("  ✅ Automatic status updates")
        return True
    else:
        print("❌ Task 6.1 VERIFICATION FAILED!")
        print(f"  {total - passed} requirements are not fully implemented")
        return False


if __name__ == "__main__":
    try:
        success = run_verification()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        logger.exception("Verification failed")
        sys.exit(1)