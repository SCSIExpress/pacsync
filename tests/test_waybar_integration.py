#!/usr/bin/env python3
"""
Test script for WayBar integration functionality.

This script tests the WayBar integration features of the Pacman Sync Utility client
to ensure proper JSON output, click handling, and status querying.
"""

import sys
import json
import subprocess
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_waybar_status_json():
    """Test JSON status output for WayBar."""
    print("Testing WayBar JSON status output...")
    
    try:
        # Test basic JSON status
        result = subprocess.run([
            sys.executable, "client/main.py", "--status", "--json"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"❌ JSON status failed with exit code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
        
        # Parse JSON output
        try:
            status_data = json.loads(result.stdout.strip())
            required_fields = ["text", "alt", "class", "tooltip"]
            
            for field in required_fields:
                if field not in status_data:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            print(f"✅ JSON status output valid: {status_data}")
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON output: {e}")
            print(f"Output: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ JSON status command timed out")
        return False
    except Exception as e:
        print(f"❌ JSON status test failed: {e}")
        return False


def test_waybar_config_template():
    """Test WayBar configuration template output."""
    print("Testing WayBar configuration template...")
    
    try:
        result = subprocess.run([
            sys.executable, "client/main.py", "--waybar-config"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"❌ WayBar config failed with exit code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
        
        # Parse JSON configuration
        try:
            config_data = json.loads(result.stdout.strip())
            
            if "pacman-sync" not in config_data:
                print("❌ Missing pacman-sync module in config")
                return False
            
            module_config = config_data["pacman-sync"]
            required_fields = ["exec", "interval", "return-type", "format"]
            
            for field in required_fields:
                if field not in module_config:
                    print(f"❌ Missing required config field: {field}")
                    return False
            
            print(f"✅ WayBar config template valid")
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON config: {e}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ WayBar config command timed out")
        return False
    except Exception as e:
        print(f"❌ WayBar config test failed: {e}")
        return False


def test_waybar_click_actions():
    """Test WayBar click action handling."""
    print("Testing WayBar click actions...")
    
    click_tests = [
        ("left", "show_status"),
        ("right", "show_menu"),
        ("middle", "sync"),
    ]
    
    for button, action in click_tests:
        try:
            print(f"  Testing {button} click with {action} action...")
            
            result = subprocess.run([
                sys.executable, "client/main.py", 
                "--waybar-click", button,
                "--waybar-action", action,
                "--json"
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode not in [0, 1]:  # Allow operation failures
                print(f"❌ Click action failed with unexpected exit code {result.returncode}")
                print(f"Error: {result.stderr}")
                return False
            
            # Should output JSON status even if operation fails
            try:
                status_data = json.loads(result.stdout.strip())
                if "text" not in status_data:
                    print(f"❌ Click action didn't return valid status JSON")
                    return False
                    
                print(f"✅ {button} click handled successfully")
                
            except json.JSONDecodeError:
                print(f"❌ Click action didn't return valid JSON")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"❌ Click action {button}/{action} timed out")
            return False
        except Exception as e:
            print(f"❌ Click action test failed: {e}")
            return False
    
    return True


def test_waybar_integration_module():
    """Test the WayBar integration module directly."""
    print("Testing WayBar integration module...")
    
    try:
        from client.waybar_integration import WayBarIntegration
        
        # Create WayBar integration instance
        waybar = WayBarIntegration()
        
        # Test status retrieval
        status = waybar.get_waybar_status()
        required_fields = ["text", "alt", "class", "tooltip"]
        
        for field in required_fields:
            if field not in status:
                print(f"❌ Missing field in status: {field}")
                return False
        
        print(f"✅ WayBar integration module status: {status}")
        
        # Test click action handling
        click_result = waybar.handle_click_action("left", "show_status")
        
        if "action" not in click_result or "result" not in click_result:
            print("❌ Click action result missing required fields")
            return False
        
        print(f"✅ WayBar integration module click handling works")
        
        # Test configuration template
        config = waybar.get_waybar_config_template()
        
        if "pacman-sync" not in config:
            print("❌ Config template missing pacman-sync module")
            return False
        
        print(f"✅ WayBar integration module config template works")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import WayBar integration: {e}")
        return False
    except Exception as e:
        print(f"❌ WayBar integration module test failed: {e}")
        return False


def test_status_persistence():
    """Test that status persistence works with WayBar integration."""
    print("Testing status persistence with WayBar...")
    
    try:
        from client.status_persistence import StatusPersistenceManager
        from client.qt.application import SyncStatus
        
        # Create status manager
        status_manager = StatusPersistenceManager()
        
        # Update status
        status_manager.update_status(SyncStatus.IN_SYNC)
        
        # Test that WayBar can read the status
        result = subprocess.run([
            sys.executable, "client/main.py", "--status", "--json"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"❌ Status persistence test failed with exit code {result.returncode}")
            return False
        
        try:
            status_data = json.loads(result.stdout.strip())
            if status_data.get("alt") != "in_sync":
                print(f"❌ Status persistence not working correctly: {status_data}")
                return False
            
            print("✅ Status persistence works with WayBar integration")
            return True
            
        except json.JSONDecodeError:
            print("❌ Status persistence test returned invalid JSON")
            return False
            
    except Exception as e:
        print(f"❌ Status persistence test failed: {e}")
        return False


def main():
    """Run all WayBar integration tests."""
    print("🧪 Running WayBar Integration Tests")
    print("=" * 50)
    
    tests = [
        ("JSON Status Output", test_waybar_status_json),
        ("Config Template", test_waybar_config_template),
        ("Click Actions", test_waybar_click_actions),
        ("Integration Module", test_waybar_integration_module),
        ("Status Persistence", test_status_persistence),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All WayBar integration tests passed!")
        return 0
    else:
        print("💥 Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())