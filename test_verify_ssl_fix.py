#!/usr/bin/env python3
"""
Test to verify the verify_ssl boolean conversion fix.

This test specifically checks that the verify_ssl setting is properly
converted to boolean for Qt checkbox widgets.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_verify_ssl_fix():
    """Test that verify_ssl is properly converted to boolean."""
    print("Testing verify_ssl Boolean Conversion Fix")
    print("=" * 45)
    
    # Test 1: Configuration loading
    print("\n1. Configuration Loading:")
    try:
        from client.config import ClientConfiguration
        
        config = ClientConfiguration()
        all_config = config.get_all_config()
        
        verify_ssl_raw = all_config.get('server', {}).get('verify_ssl', True)
        print(f"   Raw verify_ssl value: {verify_ssl_raw} (type: {type(verify_ssl_raw).__name__})")
        
    except Exception as e:
        print(f"   ✗ Configuration loading failed: {e}")
        return False
    
    # Test 2: Qt Application Conversion
    print("\n2. Qt Application Conversion:")
    try:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from PyQt6.QtWidgets import QApplication
        from client.qt.application import PacmanSyncApplication
        
        app = QApplication([])
        sync_app = PacmanSyncApplication([])
        sync_app.set_configuration(config)
        
        # Test the _to_bool conversion function
        test_values = [
            (True, True),
            (False, False),
            ('true', True),
            ('false', False),
            ('True', True),
            ('False', False),
            ('1', True),
            ('0', False),
            ('yes', True),
            ('no', False),
            (1, True),
            (0, False),
        ]
        
        print("   Testing _to_bool conversion function:")
        for input_val, expected in test_values:
            result = sync_app._to_bool(input_val)
            status = "✓" if result == expected else "✗"
            print(f"     {status} {input_val} ({type(input_val).__name__}) -> {result} (expected {expected})")
            if result != expected:
                return False
        
        # Test actual configuration conversion
        all_config = config.get_all_config()
        converted_verify_ssl = sync_app._to_bool(all_config.get('server', {}).get('verify_ssl', True))
        print(f"   ✓ verify_ssl converted: {converted_verify_ssl} (type: {type(converted_verify_ssl).__name__})")
        
        if not isinstance(converted_verify_ssl, bool):
            print("   ✗ verify_ssl conversion failed - not a boolean")
            return False
        
        app.quit()
        
    except Exception as e:
        print(f"   ✗ Qt application conversion failed: {e}")
        return False
    
    # Test 3: Configuration Window Creation
    print("\n3. Configuration Window Creation:")
    try:
        from client.qt.windows import ConfigurationWindow
        
        # Create configuration with proper type conversion
        current_config = {
            'server_url': config.get_server_url(),
            'api_key': config.get_api_key() or '',
            'timeout': int(config.get_server_timeout()),
            'retry_attempts': int(config.get_retry_attempts()),
            'verify_ssl': sync_app._to_bool(all_config.get('server', {}).get('verify_ssl', True)),
            'ssl_cert_path': all_config.get('server', {}).get('ssl_cert_path', ''),
            'endpoint_name': config.get_endpoint_name(),
            'show_notifications': sync_app._to_bool(config.should_show_notifications()),
            'minimize_to_tray': sync_app._to_bool(config.should_minimize_to_tray()),
        }
        
        print("   Configuration values for Qt window:")
        for key, value in current_config.items():
            if 'ssl' in key or 'notification' in key or 'tray' in key:
                print(f"     {key}: {value} (type: {type(value).__name__})")
        
        # Test window creation
        config_window = ConfigurationWindow(current_config)
        print("   ✓ ConfigurationWindow created successfully!")
        
        # Test that checkboxes are properly set
        verify_ssl_checked = config_window.verify_ssl_check.isChecked()
        print(f"   ✓ verify_ssl checkbox state: {verify_ssl_checked}")
        
        config_window.close()
        
    except Exception as e:
        print(f"   ✗ Configuration window creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """Main test function."""
    success = test_verify_ssl_fix()
    
    print("\n" + "=" * 45)
    if success:
        print("✅ VERIFY_SSL FIX TEST PASSED")
        print("\nThe verify_ssl boolean conversion issue is fixed:")
        print("• _to_bool() function handles various input types")
        print("• verify_ssl is properly converted to boolean")
        print("• Qt checkboxes receive correct boolean values")
        print("• Configuration window creates without errors")
        print("\nThe original error should no longer occur!")
        
    else:
        print("❌ VERIFY_SSL FIX TEST FAILED")
        print("The boolean conversion issue still exists")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())