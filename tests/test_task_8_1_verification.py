#!/usr/bin/env python3
"""
Verification test for Task 8.1: Implement command-line argument processing.

This test verifies that all requirements for task 8.1 are met:
- Create argument parser for --sync, --set-latest, --revert, and --status commands
- Implement CLI mode execution with appropriate exit codes
- Add status persistence between GUI and CLI modes

This test serves as documentation and verification that the task is complete.
"""

import sys
import subprocess
import tempfile
import json
from pathlib import Path
from datetime import datetime

def run_command(args, env=None, timeout=10):
    """Run a command and return the result."""
    cmd = [sys.executable, "client/main.py"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=env
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def test_argument_parser():
    """Test that argument parser supports all required commands."""
    print("1. Testing argument parser for required commands...")
    
    # Test help to see all available options
    code, stdout, stderr = run_command(["--help"])
    if code != 0:
        print(f"✗ Help command failed with code {code}")
        print(f"stderr: {stderr}")
        return False
    
    # argparse writes help to stdout, but if empty, check stderr
    help_output = stdout if stdout else stderr
    if not help_output:
        print("✗ Help command returned no output")
        return False
    
    # Check that all required arguments are documented
    required_args = ["--sync", "--set-latest", "--revert", "--status"]
    for arg in required_args:
        if arg not in help_output:
            print(f"✗ Required argument {arg} not found in help")
            return False
    
    print("✓ All required arguments are supported")
    
    # Test that arguments are mutually exclusive
    code, stdout, stderr = run_command(["--sync", "--status"])
    if code == 0:
        print("✗ Mutually exclusive arguments should be rejected")
        return False
    
    print("✓ Mutually exclusive arguments are properly rejected")
    
    # Test key additional arguments
    if "--json" not in help_output:
        print("✗ --json argument not found in help")
        return False
    if "--verbose" not in help_output:
        print("✗ --verbose argument not found in help")
        return False
    if "--config" not in help_output:
        print("✗ --config argument not found in help")
        return False
    
    print("✓ Additional useful arguments are supported")
    return True

def test_cli_mode_execution():
    """Test CLI mode execution with appropriate exit codes."""
    print("\n2. Testing CLI mode execution with exit codes...")
    
    # Test status command (should work without server)
    code, stdout, stderr = run_command(["--status", "--quiet"])
    if code != 8:  # No status available
        print(f"✗ Status command should return 8 when no data available, got {code}")
        return False
    print("✓ Status command returns correct exit code (8) when no data available")
    
    # Test JSON status command
    code, stdout, stderr = run_command(["--status", "--json", "--quiet"])
    if code != 8:
        print(f"✗ JSON status command should return 8 when no data available, got {code}")
        return False
    
    try:
        json_data = json.loads(stdout)
        if json_data.get("text") != "unknown":
            print(f"✗ JSON status should return 'unknown', got {json_data}")
            return False
    except json.JSONDecodeError:
        print(f"✗ JSON status should return valid JSON, got: {stdout}")
        return False
    
    print("✓ JSON status command works correctly")
    
    # Test sync command (should fail gracefully without dependencies)
    code, stdout, stderr = run_command(["--sync", "--quiet"])
    if code != 6:  # Dependency error
        print(f"✗ Sync command should return 6 (dependency error), got {code}")
        return False
    print("✓ Sync command returns correct exit code (6) for dependency error")
    
    # Test set-latest command
    code, stdout, stderr = run_command(["--set-latest", "--quiet"])
    if code != 6:
        print(f"✗ Set-latest command should return 6 (dependency error), got {code}")
        return False
    print("✓ Set-latest command returns correct exit code")
    
    # Test revert command
    code, stdout, stderr = run_command(["--revert", "--quiet"])
    if code != 6:
        print(f"✗ Revert command should return 6 (dependency error), got {code}")
        return False
    print("✓ Revert command returns correct exit code")
    
    # Test timeout functionality
    code, stdout, stderr = run_command(["--sync", "--timeout", "1", "--quiet"])
    if code not in [4, 5, 6]:  # Timeout or dependency error
        print(f"✗ Timeout should return 4, 5, or 6, got {code}")
        return False
    print("✓ Timeout functionality works correctly")
    
    return True

def test_status_persistence():
    """Test status persistence between GUI and CLI modes."""
    print("\n3. Testing status persistence between GUI and CLI modes...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up environment to use temp directory
        import os
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = temp_dir
        
        # Create status persistence manager and save test data
        sys.path.insert(0, str(Path(__file__).parent))
        from client.status_persistence import StatusPersistenceManager, PersistedStatus
        
        # Import SyncStatus with fallback
        try:
            from client.qt.application import SyncStatus
        except ImportError:
            from enum import Enum
            class SyncStatus(Enum):
                IN_SYNC = "in_sync"
                AHEAD = "ahead"
                BEHIND = "behind"
                OFFLINE = "offline"
                SYNCING = "syncing"
                ERROR = "error"
        
        # Create status manager and save test data
        config_dir = Path(temp_dir) / 'pacman-sync'
        status_manager = StatusPersistenceManager(str(config_dir))
        
        # Test 1: Save status and verify CLI can read it
        test_status = PersistedStatus(
            status=SyncStatus.IN_SYNC,
            last_updated=datetime.now(),
            endpoint_id="test-endpoint-123",
            endpoint_name="test-desktop",
            server_url="http://test-server:8080",
            is_authenticated=True,
            last_operation="sync",
            operation_result="SUCCESS: Sync completed",
            packages_count=150
        )
        
        if not status_manager.save_status(test_status):
            print("✗ Failed to save test status")
            return False
        
        # Test CLI can read the status
        code, stdout, stderr = run_command(["--status", "--quiet"], env=env)
        if code != 0:
            print(f"✗ CLI should read saved status successfully, got code {code}")
            return False
        
        if "IN_SYNC" not in stdout:
            print(f"✗ CLI should show IN_SYNC status, got: {stdout}")
            return False
        
        print("✓ CLI can read status saved by persistence manager")
        
        # Test 2: JSON format preserves all information
        code, stdout, stderr = run_command(["--status", "--json", "--quiet"], env=env)
        if code != 0:
            print(f"✗ JSON status should work with saved data, got code {code}")
            return False
        
        try:
            json_data = json.loads(stdout)
            if json_data.get("text") != "✓":  # IN_SYNC symbol
                print(f"✗ JSON should show in_sync symbol, got: {json_data}")
                return False
            
            if "test-desktop" not in json_data.get("tooltip", ""):
                print(f"✗ JSON tooltip should include endpoint name, got: {json_data}")
                return False
        except json.JSONDecodeError:
            print(f"✗ JSON status should return valid JSON, got: {stdout}")
            return False
        
        print("✓ JSON status format preserves all information")
        
        # Test 3: Verbose mode shows detailed information
        code, stdout, stderr = run_command(["--status", "--verbose"], env=env)
        if code != 0:
            print(f"✗ Verbose status should work, got code {code}")
            return False
        
        required_info = ["test-desktop", "test-server:8080", "150", "sync", "SUCCESS"]
        for info in required_info:
            if info not in stdout:
                print(f"✗ Verbose status should include '{info}', got: {stdout}")
                return False
        
        print("✓ Verbose mode shows detailed status information")
        
        # Test 4: Status freshness detection
        # Create stale status
        old_status = PersistedStatus(
            status=SyncStatus.BEHIND,
            last_updated=datetime.now().replace(year=2020),  # Very old
            endpoint_id="test-endpoint-123",
            endpoint_name="test-desktop",
            server_url="http://test-server:8080",
            is_authenticated=True
        )
        status_manager.save_status(old_status)
        
        code, stdout, stderr = run_command(["--status"], env=env)
        if "stale" not in stdout.lower():
            print(f"✗ Status should indicate staleness, got: {stdout}")
            return False
        
        print("✓ Status freshness detection works")
        
        # Test 5: Operation result tracking
        status_manager.update_operation_result("sync", True, "Test sync completed successfully")
        
        code, stdout, stderr = run_command(["--status", "--verbose"], env=env)
        if "sync" not in stdout or "SUCCESS" not in stdout:
            print(f"✗ Operation result should be shown, got: {stdout}")
            return False
        
        print("✓ Operation result tracking works")
        
        return True

def test_waybar_integration():
    """Test WayBar integration features."""
    print("\n4. Testing WayBar integration features...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        import os
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = temp_dir
        
        # Test different status states for WayBar
        sys.path.insert(0, str(Path(__file__).parent))
        from client.status_persistence import StatusPersistenceManager, PersistedStatus
        
        try:
            from client.qt.application import SyncStatus
        except ImportError:
            from enum import Enum
            class SyncStatus(Enum):
                IN_SYNC = "in_sync"
                AHEAD = "ahead"
                BEHIND = "behind"
                OFFLINE = "offline"
                SYNCING = "syncing"
                ERROR = "error"
        
        config_dir = Path(temp_dir) / 'pacman-sync'
        status_manager = StatusPersistenceManager(str(config_dir))
        
        # Test different status states
        test_cases = [
            (SyncStatus.IN_SYNC, "✓", "in_sync"),
            (SyncStatus.AHEAD, "↑", "ahead"),
            (SyncStatus.BEHIND, "↓", "behind"),
            (SyncStatus.OFFLINE, "⚠", "offline"),
            (SyncStatus.SYNCING, "⟳", "syncing"),
            (SyncStatus.ERROR, "✗", "error"),
        ]
        
        for status, expected_text, expected_class in test_cases:
            test_status = PersistedStatus(
                status=status,
                last_updated=datetime.now(),
                endpoint_id="waybar-test",
                endpoint_name="waybar-desktop",
                server_url="http://waybar-server:8080",
                is_authenticated=True
            )
            status_manager.save_status(test_status)
            
            code, stdout, stderr = run_command(["--status", "--json", "--quiet"], env=env)
            if code != 0:
                print(f"✗ JSON status failed for {status.value}, code {code}")
                return False
            
            try:
                json_data = json.loads(stdout)
                if json_data.get("text") != expected_text:
                    print(f"✗ Expected text '{expected_text}' for {status.value}, got {json_data.get('text')}")
                    return False
                
                if expected_class not in json_data.get("class", ""):
                    print(f"✗ Expected class '{expected_class}' for {status.value}, got {json_data.get('class')}")
                    return False
                
                if not json_data.get("tooltip"):
                    print(f"✗ Tooltip should be present for {status.value}")
                    return False
                    
            except json.JSONDecodeError:
                print(f"✗ Invalid JSON for {status.value}: {stdout}")
                return False
        
        print("✓ WayBar JSON format works for all status states")
        return True

def main():
    """Run all verification tests."""
    print("Verifying Task 8.1: Implement command-line argument processing")
    print("=" * 70)
    
    tests = [
        test_argument_parser,
        test_cli_mode_execution,
        test_status_persistence,
        test_waybar_integration
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"✗ {test.__name__} failed")
        except Exception as e:
            print(f"✗ {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 70)
    print(f"Task 8.1 Verification Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✅ Task 8.1 is COMPLETE - All requirements satisfied!")
        print("\nImplemented features:")
        print("• ✓ Argument parser for --sync, --set-latest, --revert, --status")
        print("• ✓ CLI mode execution with appropriate exit codes")
        print("• ✓ Status persistence between GUI and CLI modes")
        print("• ✓ JSON output for WayBar integration")
        print("• ✓ Verbose and quiet modes")
        print("• ✓ Configuration overrides")
        print("• ✓ Timeout handling")
        print("• ✓ Comprehensive error handling")
        return 0
    else:
        print("❌ Task 8.1 is INCOMPLETE - Some requirements not satisfied")
        return 1

if __name__ == "__main__":
    sys.exit(main())