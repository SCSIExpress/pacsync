#!/usr/bin/env python3
"""
Test to verify the complete configuration change flow.

This test simulates the user clicking OK in the configuration window
and verifies that the changes are properly applied to all components.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_config_change_flow():
    """Test the complete configuration change flow."""
    print("Testing Configuration Change Flow")
    print("=" * 40)
    
    # Test 1: Setup
    print("\n1. Setup:")
    try:
        from client.config import ClientConfiguration
        
        config = ClientConfiguration()
        original_url = config.get_server_url()
        original_timeout = config.get_server_timeout()
        
        print(f"   Original URL: {original_url}")
        print(f"   Original timeout: {original_timeout}")
        
    except Exception as e:
        print(f"   ✗ Setup failed: {e}")
        return False
    
    # Test 2: Qt Application Setup
    print("\n2. Qt Application Setup:")
    try:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from client.qt.application import PacmanSyncApplication
        
        app = QApplication([])
        sync_app = PacmanSyncApplication([])
        sync_app.set_configuration(config)
        
        # Set up callback to track configuration changes
        config_change_called = [False]
        new_config_received = [None]
        
        def test_config_callback(new_config):
            print(f"   ✓ Configuration change callback called!")
            print(f"   ✓ New server URL: {new_config.get_server_url()}")
            print(f"   ✓ New timeout: {new_config.get_server_timeout()}")
            config_change_called[0] = True
            new_config_received[0] = new_config
        
        sync_app.set_config_changed_callback(test_config_callback)
        print("   ✓ Qt application set up with configuration callback")
        
    except Exception as e:
        print(f"   ✗ Qt application setup failed: {e}")
        return False
    
    # Test 3: Simulate Configuration Change
    print("\n3. Simulate Configuration Change:")
    try:
        # Simulate settings from configuration window
        new_settings = {
            'server_url': 'http://test-flow-server:9999',
            'timeout': 60,
            'retry_attempts': 5,
            'verify_ssl': True,
            'endpoint_name': 'test-endpoint',
            'update_interval': 450,
            'show_notifications': True,
            'minimize_to_tray': False,
        }
        
        print(f"   Simulating settings change to: {new_settings['server_url']}")
        
        # Call the settings changed handler directly
        sync_app._handle_settings_changed(new_settings, config)
        
        print("   ✓ Settings change handler called")
        
    except Exception as e:
        print(f"   ✗ Configuration change simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Verify Changes Applied
    print("\n4. Verify Changes Applied:")
    try:
        # Check if configuration was updated
        updated_url = config.get_server_url()
        updated_timeout = config.get_server_timeout()
        
        print(f"   Configuration URL after change: {updated_url}")
        print(f"   Configuration timeout after change: {updated_timeout}")
        
        if updated_url == 'http://test-flow-server:9999':
            print("   ✓ Configuration URL updated correctly")
        else:
            print(f"   ✗ Configuration URL not updated: expected 'http://test-flow-server:9999', got '{updated_url}'")
            return False
        
        if updated_timeout == 60:
            print("   ✓ Configuration timeout updated correctly")
        else:
            print(f"   ✗ Configuration timeout not updated: expected 60, got {updated_timeout}")
            return False
        
        # Check if callback was called
        if config_change_called[0]:
            print("   ✓ Configuration change callback was called")
        else:
            print("   ✗ Configuration change callback was NOT called")
            return False
        
        # Check if callback received correct config
        if new_config_received[0] and new_config_received[0].get_server_url() == 'http://test-flow-server:9999':
            print("   ✓ Callback received updated configuration")
        else:
            print("   ✗ Callback did not receive updated configuration")
            return False
        
    except Exception as e:
        print(f"   ✗ Verification failed: {e}")
        return False
    
    # Test 5: Verify Persistence
    print("\n5. Verify Persistence:")
    try:
        # Create new config instance to test persistence
        config2 = ClientConfiguration()
        persisted_url = config2.get_server_url()
        persisted_timeout = config2.get_server_timeout()
        
        if persisted_url == 'http://test-flow-server:9999':
            print("   ✓ Configuration changes persisted to file")
        else:
            print(f"   ✗ Configuration not persisted: got '{persisted_url}'")
            return False
        
        # Restore original configuration
        config.set_config('server.url', original_url)
        config.set_config('server.timeout', original_timeout)
        config.save_configuration()
        print("   ✓ Original configuration restored")
        
        app.quit()
        
    except Exception as e:
        print(f"   ✗ Persistence verification failed: {e}")
        return False
    
    return True

def main():
    """Main test function."""
    success = test_config_change_flow()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ CONFIGURATION CHANGE FLOW TEST PASSED")
        print("\nThe complete configuration change flow is working:")
        print("• Settings are saved to configuration file")
        print("• Configuration is reloaded from file")
        print("• Configuration change callback is called")
        print("• Components receive updated configuration")
        print("• Changes persist across application restarts")
        
        print("\nIf you're still seeing the wrong server URL, check:")
        print("1. Are you looking at the right log output?")
        print("2. Is there another instance of the client running?")
        print("3. Are there any cached connections or authentication tokens?")
        
    else:
        print("❌ CONFIGURATION CHANGE FLOW TEST FAILED")
        print("There may be an issue with the configuration change process")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())