#!/usr/bin/env python3
"""
Debug script to show what server URLs are being used by different components.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def debug_server_urls():
    """Debug server URLs in different components."""
    print("Debugging Server URLs")
    print("=" * 30)
    
    # Check configuration file
    print("\n1. Configuration File:")
    try:
        from client.config import ClientConfiguration
        
        config = ClientConfiguration()
        config_url = config.get_server_url()
        config_file = config.get_config_file_path()
        
        print(f"   Config file: {config_file}")
        print(f"   Server URL from config: {config_url}")
        
        # Check raw config data
        all_config = config.get_all_config()
        raw_url = all_config.get('server', {}).get('url', 'NOT SET')
        print(f"   Raw URL from config data: {raw_url}")
        
    except Exception as e:
        print(f"   ✗ Configuration check failed: {e}")
        return
    
    # Check if there are any environment variable overrides
    print("\n2. Environment Variables:")
    import os
    env_vars = [
        'PACMAN_SYNC_SERVER_URL',
        'SERVER_URL',
        'PACMAN_SYNC_URL'
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"   {var}: {value}")
        else:
            print(f"   {var}: not set")
    
    # Check if there are multiple config files
    print("\n3. Potential Config File Locations:")
    potential_configs = [
        Path.home() / '.pacsync' / 'client.conf',
        Path.home() / '.config' / 'pacman-sync' / 'client.conf',
        Path('/etc/pacman-sync/client/client.conf'),
        Path('/etc/pacman-sync-utility/client.conf'),
    ]
    
    for config_path in potential_configs:
        if config_path.exists():
            print(f"   ✓ EXISTS: {config_path}")
            try:
                # Try to read the URL from this config
                from configparser import ConfigParser
                parser = ConfigParser()
                parser.read(str(config_path))
                url = parser.get('server', 'url', fallback='NOT SET')
                print(f"     Server URL: {url}")
            except Exception as e:
                print(f"     Error reading: {e}")
        else:
            print(f"   - not found: {config_path}")
    
    # Check current working directory for any config files
    print("\n4. Current Directory Config Files:")
    cwd = Path.cwd()
    for config_file in cwd.glob('**/client.conf'):
        print(f"   Found: {config_file}")
    
    # Show what the API client would use
    print("\n5. API Client Configuration:")
    try:
        from client.api_client import PacmanSyncAPIClient
        
        # Create API client with current config
        api_client = PacmanSyncAPIClient(
            server_url=config.get_server_url(),
            timeout=config.get_server_timeout()
        )
        
        print(f"   API client server URL: {api_client.server_url}")
        print(f"   API client timeout: {api_client.timeout}")
        
        # Check if there are any session or connection objects
        if hasattr(api_client, '_session') and api_client._session:
            print(f"   API client has active session: Yes")
        else:
            print(f"   API client has active session: No")
        
    except Exception as e:
        print(f"   ✗ API client check failed: {e}")

def main():
    """Main debug function."""
    debug_server_urls()
    
    print("\n" + "=" * 30)
    print("Debug complete. If you're still seeing the wrong URL:")
    print("1. Check if there are multiple config files")
    print("2. Check if environment variables are overriding settings")
    print("3. Make sure no other client instances are running")
    print("4. Check the application logs for which URL is actually being used")

if __name__ == "__main__":
    main()