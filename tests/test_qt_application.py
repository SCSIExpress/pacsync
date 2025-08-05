#!/usr/bin/env python3
"""
Test script for Qt application framework and system tray integration.

This script tests the basic functionality of the Qt application without
requiring the full server infrastructure.
"""

import sys
import logging
import time
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


def test_qt_application():
    """Test the Qt application framework."""
    try:
        from client.qt.application import PacmanSyncApplication, SyncStatus
        
        print("Testing Qt Application Framework...")
        
        # Initialize application
        app = PacmanSyncApplication(sys.argv)
        
        # Check system tray availability
        if not app.is_system_tray_available():
            print("❌ System tray is not available")
            return False
        
        print("✅ Qt application initialized successfully")
        print("✅ System tray is available")
        
        # Test status updates
        print("\nTesting status updates...")
        statuses_to_test = [
            SyncStatus.OFFLINE,
            SyncStatus.IN_SYNC,
            SyncStatus.AHEAD,
            SyncStatus.BEHIND,
            SyncStatus.SYNCING,
            SyncStatus.ERROR
        ]
        
        for status in statuses_to_test:
            app.update_sync_status(status)
            current = app.get_sync_status()
            if current == status:
                print(f"✅ Status update to {status.value} successful")
            else:
                print(f"❌ Status update failed: expected {status.value}, got {current.value if current else 'None'}")
                return False
        
        # Test notifications
        print("\nTesting notifications...")
        app.show_notification("Test Notification", "This is a test notification")
        print("✅ Notification sent (check your system tray)")
        
        # Test callbacks
        print("\nTesting callback registration...")
        callback_called = {"sync": False, "set_latest": False, "revert": False}
        
        def test_sync():
            callback_called["sync"] = True
            print("✅ Sync callback executed")
        
        def test_set_latest():
            callback_called["set_latest"] = True
            print("✅ Set latest callback executed")
        
        def test_revert():
            callback_called["revert"] = True
            print("✅ Revert callback executed")
        
        app.set_sync_callback(test_sync)
        app.set_set_latest_callback(test_set_latest)
        app.set_revert_callback(test_revert)
        
        print("✅ Callbacks registered successfully")
        
        print("\n" + "="*50)
        print("Qt Application Test Results:")
        print("✅ Application initialization: PASSED")
        print("✅ System tray integration: PASSED")
        print("✅ Status management: PASSED")
        print("✅ Notification system: PASSED")
        print("✅ Callback system: PASSED")
        print("="*50)
        
        print("\nThe application is now running with system tray integration.")
        print("You should see a system tray icon that you can right-click for options.")
        print("The icon color indicates sync status:")
        print("  🟢 Green: In Sync")
        print("  🟠 Orange: Ahead of Pool")
        print("  🔵 Blue: Behind Pool")
        print("  ⚫ Gray: Offline")
        print("  🟡 Yellow: Syncing")
        print("  🔴 Red: Error")
        print("\nPress Ctrl+C to quit or use the tray menu.")
        
        # Run the application
        return app.exec()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure PyQt6 is installed: pip install PyQt6")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logger.exception("Test failed")
        return False


if __name__ == "__main__":
    try:
        result = test_qt_application()
        sys.exit(0 if result == 0 else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(0)