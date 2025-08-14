#!/usr/bin/env python3
"""
Test script to verify the Qt ConfigurationWindow can be created without type errors.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def _to_bool(value) -> bool:
    """Convert various value types to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    if isinstance(value, (int, float)):
        return bool(value)
    return bool(value)

def test_config_window_creation():
    """Test that ConfigurationWindow can be created without type errors."""
    print("Testing ConfigurationWindow creation...")
    
    try:
        # Set up minimal Qt environment
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # Avoid display issues
        
        from PyQt6.QtWidgets import QApplication
        from client.config import ClientConfiguration
        from client.qt.windows import ConfigurationWindow
        
        # Create Qt application
        app = QApplication([])
        
        # Load configuration
        config = ClientConfiguration()
        all_config = config.get_all_config()
        
        # Convert configuration to Qt format with proper type conversion
        current_config = {
            # Server settings
            'server_url': config.get_server_url(),
            'api_key': config.get_api_key() or '',
            'timeout': int(config.get_server_timeout()),  # Convert float to int
            'retry_attempts': int(config.get_retry_attempts()),  # Ensure int
            'verify_ssl': _to_bool(all_config.get('server', {}).get('verify_ssl', True)),
            'ssl_cert_path': all_config.get('server', {}).get('ssl_cert_path', ''),
            
            # Client settings
            'endpoint_name': config.get_endpoint_name(),
            'pool_id': config.get_pool_id() or '',  # Read-only, for display
            'update_interval': int(config.get_update_interval()),  # Convert to int
            'auto_register': _to_bool(all_config.get('client', {}).get('auto_register', True)),
            'auto_sync': _to_bool(config.is_auto_sync_enabled()),
            'sync_on_startup': _to_bool(all_config.get('client', {}).get('sync_on_startup', False)),
            'confirm_operations': _to_bool(all_config.get('operations', {}).get('confirm_destructive_operations', True)),
            'exclude_packages': all_config.get('operations', {}).get('exclude_packages', []),
            'conflict_resolution': all_config.get('operations', {}).get('conflict_resolution', 'manual'),
            
            # Logging settings
            'log_level': config.get_log_level(),
            'log_file': config.get_log_file() or '',
            
            # UI settings
            'show_notifications': _to_bool(config.should_show_notifications()),
            'minimize_to_tray': _to_bool(config.should_minimize_to_tray()),
            'start_minimized': _to_bool(all_config.get('ui', {}).get('start_minimized', False)),
            'theme': all_config.get('ui', {}).get('theme', 'System Default'),
            'font_size': int(all_config.get('ui', {}).get('font_size', 10)),  # Ensure int
            
            # WayBar settings
            'enable_waybar': _to_bool(all_config.get('waybar', {}).get('enabled', False)),
            'waybar_format': all_config.get('waybar', {}).get('format', '')
        }
        
        print("Configuration values and types:")
        for key, value in current_config.items():
            print(f"  {key}: {value} ({type(value).__name__})")
        
        # Test creating the ConfigurationWindow
        print("\nCreating ConfigurationWindow...")
        config_window = ConfigurationWindow(current_config)
        print("✓ ConfigurationWindow created successfully!")
        
        # Clean up
        config_window.close()
        app.quit()
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to create ConfigurationWindow: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("Qt ConfigurationWindow Type Safety Test")
    print("=" * 50)
    
    success = test_config_window_creation()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ Test PASSED - ConfigurationWindow can be created without type errors")
        print("\nThe Qt configuration menu should now work properly!")
    else:
        print("✗ Test FAILED - There are still type issues")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())