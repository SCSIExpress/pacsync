#!/usr/bin/env python3
"""
Test script to verify configuration integration with Qt menus.

This script tests that the Qt configuration window can properly load and save
configuration files from the expected locations.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_config_loading():
    """Test configuration loading from different locations."""
    print("Testing configuration loading...")
    
    from client.config import ClientConfiguration
    
    # Test 1: Load default configuration
    print("\n1. Testing default configuration loading:")
    config = ClientConfiguration()
    print(f"   Config file path: {config.get_config_file_path()}")
    print(f"   Server URL: {config.get_server_url()}")
    print(f"   Endpoint name: {config.get_endpoint_name()}")
    print(f"   Config file exists: {os.path.exists(config.get_config_file_path())}")
    
    # Test 2: Check new simplified config path
    expected_path = str(Path.home() / '.pacsync' / 'client.conf')
    print(f"\n2. Expected config path: {expected_path}")
    print(f"   Matches actual path: {config.get_config_file_path() == expected_path}")
    
    # Test 3: Check if old system config paths exist (for migration info)
    old_system_paths = [
        "/etc/pacman-sync/client/client.conf",
        "/etc/pacman-sync-utility/client.conf"
    ]
    
    print("\n3. Checking old system configuration paths (for reference):")
    for path in old_system_paths:
        exists = os.path.exists(path)
        print(f"   {path}: exists={exists}")
    
    # Test 4: Test configuration modification and saving
    print("\n4. Testing configuration modification:")
    original_url = config.get_server_url()
    test_url = "http://test-server:9999"
    
    config.set_config('server.url', test_url)
    print(f"   Modified server URL to: {config.get_server_url()}")
    
    try:
        config.save_configuration()
        print(f"   Configuration saved successfully to: {config.get_config_file_path()}")
        
        # Reload and verify
        config2 = ClientConfiguration(config.get_config_file_path())
        saved_url = config2.get_server_url()
        print(f"   Reloaded server URL: {saved_url}")
        
        if saved_url == test_url:
            print("   ✓ Configuration save/load test PASSED")
        else:
            print("   ✗ Configuration save/load test FAILED")
        
        # Restore original value
        config.set_config('server.url', original_url)
        config.save_configuration()
        print(f"   Restored original server URL: {original_url}")
        
    except Exception as e:
        print(f"   ✗ Configuration save failed: {e}")
    
    return config

def test_qt_integration():
    """Test Qt configuration window integration."""
    print("\n" + "="*60)
    print("Testing Qt configuration integration...")
    
    try:
        from client.config import ClientConfiguration
        
        # Load configuration
        config = ClientConfiguration()
        
        # Test configuration conversion for Qt window
        print("\n1. Testing configuration conversion for Qt:")
        all_config = config.get_all_config()
        
        # Convert to Qt format (similar to what's done in _handle_config_request)
        qt_config = {
            'server_url': config.get_server_url(),
            'api_key': config.get_api_key() or '',
            'timeout': int(config.get_server_timeout()),  # Convert to int for QSpinBox
            'retry_attempts': int(config.get_retry_attempts()),  # Convert to int for QSpinBox
            'endpoint_name': config.get_endpoint_name(),
            'pool_id': config.get_pool_id() or '',
            'update_interval': int(config.get_update_interval()),  # Convert to int for QSpinBox
            'auto_sync': config.is_auto_sync_enabled(),
            'log_level': config.get_log_level(),
            'log_file': config.get_log_file() or '',
            'show_notifications': config.should_show_notifications(),
            'minimize_to_tray': config.should_minimize_to_tray(),
        }
        
        print("   Qt configuration format:")
        for key, value in qt_config.items():
            print(f"     {key}: {value}")
        
        print("\n2. Testing Qt class imports:")
        try:
            from client.qt.application import PacmanSyncApplication
            print("   ✓ PacmanSyncApplication class is importable")
        except ImportError as e:
            print(f"   ✗ Failed to import PacmanSyncApplication: {e}")
        
        try:
            from client.qt.windows import ConfigurationWindow
            print("   ✓ ConfigurationWindow class is importable")
        except ImportError as e:
            print(f"   ✗ Failed to import ConfigurationWindow: {e}")
        
        print("   ✓ Qt integration test completed (import test only)")
        
    except ImportError as e:
        print(f"   ✗ Qt dependencies not available: {e}")
        print("   Install PyQt6 to test Qt integration: pip install PyQt6")
    except Exception as e:
        print(f"   ✗ Qt integration test failed: {e}")

def main():
    """Main test function."""
    print("Pacman Sync Utility - Configuration Integration Test")
    print("="*60)
    
    # Test configuration loading
    config = test_config_loading()
    
    # Test Qt integration
    test_qt_integration()
    
    print("\n" + "="*60)
    print("Test Summary:")
    print(f"Configuration file: {config.get_config_file_path()}")
    print(f"File exists: {os.path.exists(config.get_config_file_path())}")
    print(f"File writable: {config._is_config_writable()}")
    
    print("\nTo test the Qt configuration window:")
    print("1. Run the client in GUI mode: python client/main.py")
    print("2. Right-click the system tray icon")
    print("3. Select 'Configuration...'")
    print("4. Modify settings and click 'Save'")
    print("5. Check that changes are saved to ~/.pacsync/client.conf")
    print("6. Note: Pool ID is now assigned by server, not user-configurable")

if __name__ == "__main__":
    main()