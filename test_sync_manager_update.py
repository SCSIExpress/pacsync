#!/usr/bin/env python3
"""
Test to verify that SyncManager properly updates its configuration.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_sync_manager_update():
    """Test SyncManager configuration update."""
    print("Testing SyncManager Configuration Update")
    print("=" * 45)
    
    # Test 1: Create SyncManager with initial config
    print("\n1. Create SyncManager:")
    try:
        from client.config import ClientConfiguration
        from client.sync_manager import SyncManager
        
        # Create initial config
        config1 = ClientConfiguration()
        original_url = config1.get_server_url()
        original_timeout = config1.get_server_timeout()
        
        print(f"   Initial URL: {original_url}")
        print(f"   Initial timeout: {original_timeout}")
        
        # Create SyncManager (but don't start it to avoid network calls)
        sync_manager = SyncManager(config1)
        
        print(f"   SyncManager API client URL: {sync_manager._api_client.server_url}")
        print(f"   SyncManager API client timeout: {sync_manager._api_client.timeout}")
        
    except Exception as e:
        print(f"   ✗ SyncManager creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Update configuration
    print("\n2. Update Configuration:")
    try:
        # Create new config with different settings
        config2 = ClientConfiguration()
        config2.set_config('server.url', 'http://updated-sync-server:7777')
        config2.set_config('server.timeout', 90)
        
        new_url = config2.get_server_url()
        new_timeout = config2.get_server_timeout()
        
        print(f"   New URL: {new_url}")
        print(f"   New timeout: {new_timeout}")
        
        # Update SyncManager configuration
        print("   Calling sync_manager.update_configuration()...")
        sync_manager.update_configuration(config2)
        
        print("   ✓ Configuration update completed")
        
    except Exception as e:
        print(f"   ✗ Configuration update failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Verify updates applied
    print("\n3. Verify Updates Applied:")
    try:
        # Check SyncManager's config
        updated_config_url = sync_manager.config.get_server_url()
        updated_config_timeout = sync_manager.config.get_server_timeout()
        
        print(f"   SyncManager config URL: {updated_config_url}")
        print(f"   SyncManager config timeout: {updated_config_timeout}")
        
        # Check API client
        api_client_url = sync_manager._api_client.server_url
        api_client_timeout = sync_manager._api_client.timeout
        
        print(f"   API client URL: {api_client_url}")
        print(f"   API client timeout: {api_client_timeout}")
        
        # Verify URL update
        if updated_config_url == 'http://updated-sync-server:7777':
            print("   ✓ SyncManager config URL updated correctly")
        else:
            print(f"   ✗ SyncManager config URL not updated: got '{updated_config_url}'")
            return False
        
        if api_client_url == 'http://updated-sync-server:7777':
            print("   ✓ API client URL updated correctly")
        else:
            print(f"   ✗ API client URL not updated: got '{api_client_url}'")
            return False
        
        # Verify timeout update
        if updated_config_timeout == 90:
            print("   ✓ SyncManager config timeout updated correctly")
        else:
            print(f"   ✗ SyncManager config timeout not updated: got {updated_config_timeout}")
            return False
        
        # Check if timeout object was updated (it's a ClientTimeout object)
        if hasattr(api_client_timeout, 'total') and api_client_timeout.total == 90:
            print("   ✓ API client timeout updated correctly")
        else:
            print(f"   ✗ API client timeout not updated correctly: {api_client_timeout}")
            return False
        
    except Exception as e:
        print(f"   ✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Cleanup
    print("\n4. Cleanup:")
    try:
        sync_manager.stop()
        print("   ✓ SyncManager stopped")
        
    except Exception as e:
        print(f"   ✗ Cleanup failed: {e}")
        return False
    
    return True

def main():
    """Main test function."""
    success = test_sync_manager_update()
    
    print("\n" + "=" * 45)
    if success:
        print("✅ SYNC MANAGER UPDATE TEST PASSED")
        print("\nSyncManager configuration updates are working:")
        print("• SyncManager config is updated")
        print("• API client server URL is updated")
        print("• API client timeout is updated")
        print("• Changes are applied immediately")
        
        print("\nThe configuration refresh should now work properly!")
        print("If you're still seeing the old URL, try:")
        print("1. Restart the client completely")
        print("2. Check for multiple running instances")
        print("3. Clear any cached authentication tokens")
        
    else:
        print("❌ SYNC MANAGER UPDATE TEST FAILED")
        print("There are still issues with SyncManager configuration updates")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())