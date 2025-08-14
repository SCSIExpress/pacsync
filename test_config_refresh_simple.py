#!/usr/bin/env python3
"""
Simple test for configuration refresh functionality.

This test focuses on the core configuration refresh without complex async operations.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_simple_config_refresh():
    """Test basic configuration refresh functionality."""
    print("Testing Simple Configuration Refresh")
    print("=" * 40)
    
    # Test 1: Basic configuration operations
    print("\n1. Basic Configuration Operations:")
    try:
        from client.config import ClientConfiguration
        
        config = ClientConfiguration()
        original_url = config.get_server_url()
        original_timeout = config.get_server_timeout()
        
        print(f"   Original URL: {original_url}")
        print(f"   Original timeout: {original_timeout}")
        
        # Modify and save
        test_url = "http://refresh-test:8080"
        test_timeout = 45
        
        config.set_config('server.url', test_url)
        config.set_config('server.timeout', test_timeout)
        config.save_configuration()
        
        print(f"   ✓ Modified URL to: {test_url}")
        print(f"   ✓ Modified timeout to: {test_timeout}")
        
        # Test reload
        config.reload_configuration()
        reloaded_url = config.get_server_url()
        reloaded_timeout = config.get_server_timeout()
        
        if reloaded_url == test_url and reloaded_timeout == test_timeout:
            print("   ✓ Configuration reload successful")
        else:
            print(f"   ✗ Reload failed: URL={reloaded_url}, timeout={reloaded_timeout}")
            return False
        
        # Restore original
        config.set_config('server.url', original_url)
        config.set_config('server.timeout', original_timeout)
        config.save_configuration()
        print("   ✓ Original configuration restored")
        
    except Exception as e:
        print(f"   ✗ Basic configuration test failed: {e}")
        return False
    
    # Test 2: Qt Application Configuration Refresh
    print("\n2. Qt Application Configuration Refresh:")
    try:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from client.qt.application import PacmanSyncApplication
        
        app = QApplication([])
        sync_app = PacmanSyncApplication([])
        sync_app.set_configuration(config)
        
        # Test the reload_configuration method
        original_app_url = sync_app._config.get_server_url()
        print(f"   Qt app original URL: {original_app_url}")
        
        # Modify config file externally
        config.set_config('server.url', 'http://qt-test:7777')
        config.save_configuration()
        
        # Reload in Qt app
        sync_app.reload_configuration()
        reloaded_app_url = sync_app._config.get_server_url()
        
        if reloaded_app_url == 'http://qt-test:7777':
            print("   ✓ Qt application configuration refresh successful")
        else:
            print(f"   ✗ Qt app refresh failed: got {reloaded_app_url}")
            return False
        
        # Restore and cleanup
        config.set_config('server.url', original_url)
        config.save_configuration()
        
        app.quit()
        
    except ImportError:
        print("   ⚠ Qt not available - skipping Qt test")
    except Exception as e:
        print(f"   ✗ Qt application test failed: {e}")
        return False
    
    # Test 3: Configuration Window Integration
    print("\n3. Configuration Window Integration:")
    try:
        from client.qt.windows import ConfigurationWindow
        
        # Test configuration conversion
        qt_config = {
            'server_url': config.get_server_url(),
            'timeout': int(config.get_server_timeout()),
            'endpoint_name': config.get_endpoint_name(),
            'update_interval': int(config.get_update_interval()),
            'show_notifications': bool(config.should_show_notifications()),
        }
        
        print("   ✓ Configuration converted for Qt window")
        print(f"   ✓ Server URL: {qt_config['server_url']}")
        print(f"   ✓ Timeout: {qt_config['timeout']} (type: {type(qt_config['timeout']).__name__})")
        print(f"   ✓ Notifications: {qt_config['show_notifications']} (type: {type(qt_config['show_notifications']).__name__})")
        
        # Test window creation (without showing)
        if 'app' in locals():
            config_window = ConfigurationWindow(qt_config)
            config_window.close()
            print("   ✓ Configuration window created successfully")
        
    except Exception as e:
        print(f"   ✗ Configuration window test failed: {e}")
        return False
    
    return True

def main():
    """Main test function."""
    success = test_simple_config_refresh()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ SIMPLE CONFIGURATION REFRESH TEST PASSED")
        print("\nKey Features Working:")
        print("• Configuration save/reload cycle")
        print("• Qt application configuration refresh")
        print("• Type-safe configuration conversion")
        print("• Configuration window integration")
        
        print("\nUser Workflow:")
        print("1. User opens configuration window")
        print("2. User modifies settings")
        print("3. User clicks Apply or OK")
        print("4. Settings are saved and applied immediately")
        print("5. Application uses new settings without restart")
        
    else:
        print("❌ SIMPLE CONFIGURATION REFRESH TEST FAILED")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())