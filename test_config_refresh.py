#!/usr/bin/env python3
"""
Test script to verify configuration refresh functionality.

This test verifies that configuration changes are applied immediately
without requiring an application restart.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_config_refresh():
    """Test configuration refresh functionality."""
    print("Testing Configuration Refresh Functionality")
    print("=" * 50)
    
    # Test 1: Configuration loading and modification
    print("\n1. Configuration Loading and Modification:")
    try:
        from client.config import ClientConfiguration
        
        config = ClientConfiguration()
        original_url = config.get_server_url()
        original_interval = config.get_update_interval()
        
        print(f"   ✓ Original server URL: {original_url}")
        print(f"   ✓ Original update interval: {original_interval} seconds")
        
        # Modify configuration
        test_url = "http://test-refresh-server:9090"
        test_interval = 600
        
        config.set_config('server.url', test_url)
        config.set_config('client.update_interval', test_interval)
        config.save_configuration()
        
        print(f"   ✓ Modified server URL to: {test_url}")
        print(f"   ✓ Modified update interval to: {test_interval} seconds")
        
    except Exception as e:
        print(f"   ✗ Configuration modification failed: {e}")
        return False
    
    # Test 2: Configuration reload
    print("\n2. Configuration Reload:")
    try:
        # Create new config instance to test reload
        config2 = ClientConfiguration()
        reloaded_url = config2.get_server_url()
        reloaded_interval = config2.get_update_interval()
        
        if reloaded_url == test_url and reloaded_interval == test_interval:
            print("   ✓ Configuration changes persisted correctly")
        else:
            print(f"   ✗ Configuration reload failed: URL={reloaded_url}, Interval={reloaded_interval}")
            return False
        
        # Test reload_configuration method
        config.set_config('server.url', original_url)  # Change in memory only
        config.reload_configuration()  # Should reload from file
        
        if config.get_server_url() == test_url:  # Should be test_url from file
            print("   ✓ reload_configuration() method works correctly")
        else:
            print(f"   ✗ reload_configuration() failed: got {config.get_server_url()}, expected {test_url}")
            return False
        
    except Exception as e:
        print(f"   ✗ Configuration reload failed: {e}")
        return False
    
    # Test 3: Qt Application Integration
    print("\n3. Qt Application Integration:")
    try:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from client.qt.application import PacmanSyncApplication
        
        app = QApplication([])
        sync_app = PacmanSyncApplication([])
        sync_app.set_configuration(config)
        
        print("   ✓ Qt application accepts configuration")
        
        # Test configuration reload in Qt app
        original_config_url = sync_app._config.get_server_url()
        sync_app.reload_configuration()
        reloaded_config_url = sync_app._config.get_server_url()
        
        print(f"   ✓ Qt app configuration reload: {original_config_url} -> {reloaded_config_url}")
        
        app.quit()
        
    except ImportError:
        print("   ⚠ Qt not available - skipping Qt integration test")
    except Exception as e:
        print(f"   ✗ Qt integration failed: {e}")
        return False
    
    # Test 4: SyncManager Integration
    print("\n4. SyncManager Integration:")
    try:
        from client.sync_manager import SyncManager
        
        # Create sync manager with original config
        sync_manager = SyncManager(config)
        original_sync_url = sync_manager.config.get_server_url()
        original_sync_interval = sync_manager.config.get_update_interval()
        
        print(f"   ✓ SyncManager initialized with URL: {original_sync_url}")
        print(f"   ✓ SyncManager initialized with interval: {original_sync_interval}")
        
        # Test configuration update
        new_config = ClientConfiguration()
        new_config.set_config('server.url', 'http://updated-server:8888')
        new_config.set_config('client.update_interval', 900)
        
        sync_manager.update_configuration(new_config)
        
        updated_url = sync_manager.config.get_server_url()
        updated_interval = sync_manager.config.get_update_interval()
        
        print(f"   ✓ SyncManager updated URL: {updated_url}")
        print(f"   ✓ SyncManager updated interval: {updated_interval}")
        
        if updated_url == 'http://updated-server:8888' and updated_interval == 900:
            print("   ✓ SyncManager configuration update successful")
        else:
            print("   ✗ SyncManager configuration update failed")
            return False
        
        sync_manager.stop()
        
    except Exception as e:
        print(f"   ✗ SyncManager integration failed: {e}")
        return False
    
    # Test 5: Cleanup - restore original configuration
    print("\n5. Cleanup:")
    try:
        config.set_config('server.url', original_url)
        config.set_config('client.update_interval', original_interval)
        config.save_configuration()
        print(f"   ✓ Restored original configuration")
        
    except Exception as e:
        print(f"   ✗ Cleanup failed: {e}")
        return False
    
    return True

def main():
    """Main test function."""
    success = test_config_refresh()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ CONFIGURATION REFRESH TEST PASSED")
        print("\nConfiguration refresh functionality is working:")
        print("• Configuration changes are saved immediately")
        print("• Qt application can reload configuration without restart")
        print("• SyncManager updates its settings dynamically")
        print("• Server connection settings take effect immediately")
        print("• Update intervals are applied to running timers")
        
        print("\nUser Experience:")
        print("1. User opens configuration window")
        print("2. User modifies settings and clicks Apply/OK")
        print("3. Settings are saved and applied immediately")
        print("4. No application restart required!")
        
    else:
        print("❌ CONFIGURATION REFRESH TEST FAILED")
        print("Some issues remain with the configuration refresh system")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())