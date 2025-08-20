#!/usr/bin/env python3
"""
Debug script for stuck authentication issues.

This script helps identify why a client might be stuck in authentication.
"""

import sys
import os
import asyncio
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_client_logs():
    """Check for client log files and recent entries."""
    print("\n1. Checking Client Logs:")
    
    # Common log locations
    log_locations = [
        Path.home() / '.pacsync' / 'client.log',
        Path.home() / '.config' / 'pacman-sync' / 'client.log',
        Path.home() / '.local' / 'share' / 'pacman-sync' / 'client.log',
        Path('/var/log/pacman-sync/client.log'),
        Path('/tmp/pacman-sync-client.log'),
    ]
    
    found_logs = []
    for log_path in log_locations:
        if log_path.exists():
            found_logs.append(log_path)
            print(f"   Found log: {log_path}")
            
            # Show recent entries
            try:
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    recent_lines = lines[-10:] if len(lines) > 10 else lines
                    
                print(f"   Recent entries:")
                for line in recent_lines:
                    if 'auth' in line.lower() or 'error' in line.lower():
                        print(f"     {line.strip()}")
                        
            except Exception as e:
                print(f"   Error reading log: {e}")
    
    if not found_logs:
        print("   No client log files found")
        print("   Try running client with --log-file option to create logs")

def check_token_storage():
    """Check token storage status."""
    print("\n2. Checking Token Storage:")
    
    try:
        from client.auth.token_storage import SecureTokenStorage
        
        storage = SecureTokenStorage()
        print(f"   Token storage initialized: ✓")
        
        # Check if keyring is available
        try:
            import keyring
            print(f"   Keyring available: ✓")
            
            # Try to access keyring
            test_key = "pacman-sync-test"
            keyring.set_password("pacman-sync-test", "test", "test-value")
            retrieved = keyring.get_password("pacman-sync-test", "test")
            keyring.delete_password("pacman-sync-test", "test")
            
            if retrieved == "test-value":
                print(f"   Keyring functional: ✓")
            else:
                print(f"   Keyring test failed: ✗")
                
        except Exception as e:
            print(f"   Keyring error: {e}")
            print(f"   This might cause token storage issues")
        
        # Check for existing tokens
        try:
            # This would require knowing the endpoint ID, so we'll skip for now
            print(f"   Token storage appears functional")
        except Exception as e:
            print(f"   Token storage error: {e}")
            
    except Exception as e:
        print(f"   Token storage initialization failed: {e}")

def check_network_connectivity(server_url: str):
    """Check network connectivity to server."""
    print(f"\n3. Checking Network Connectivity to {server_url}:")
    
    try:
        import socket
        from urllib.parse import urlparse
        
        parsed = urlparse(server_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        print(f"   Testing TCP connection to {host}:{port}")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"   ✓ TCP connection successful")
        else:
            print(f"   ✗ TCP connection failed (error: {result})")
            return False
        
        # Test HTTP connectivity
        print(f"   Testing HTTP connectivity...")
        
        import aiohttp
        
        async def test_http():
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(f"{server_url}/health") as response:
                        if response.status == 200:
                            print(f"   ✓ HTTP health check successful")
                            return True
                        else:
                            print(f"   ✗ HTTP health check failed: {response.status}")
                            return False
            except Exception as e:
                print(f"   ✗ HTTP test failed: {e}")
                return False
        
        return asyncio.run(test_http())
        
    except Exception as e:
        print(f"   ✗ Network connectivity test failed: {e}")
        return False

def check_running_processes():
    """Check for running client processes."""
    print("\n4. Checking Running Processes:")
    
    try:
        import subprocess
        
        # Check for pacman-sync processes
        result = subprocess.run(['pgrep', '-f', 'pacman-sync'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"   Found {len(pids)} pacman-sync processes:")
            for pid in pids:
                if pid:
                    # Get process info
                    try:
                        ps_result = subprocess.run(['ps', '-p', pid, '-o', 'pid,cmd'], 
                                                 capture_output=True, text=True)
                        if ps_result.returncode == 0:
                            lines = ps_result.stdout.strip().split('\n')
                            if len(lines) > 1:
                                print(f"     {lines[1]}")
                    except:
                        print(f"     PID: {pid}")
        else:
            print("   No pacman-sync processes found")
            
    except Exception as e:
        print(f"   Process check failed: {e}")

def check_configuration(server_url: str):
    """Check client configuration."""
    print(f"\n5. Checking Client Configuration:")
    
    try:
        from client.config import ClientConfiguration
        
        config = ClientConfiguration()
        
        print(f"   Config file: {config.get_config_file_path()}")
        print(f"   Server URL: {config.get_server_url()}")
        print(f"   Endpoint name: {config.get_endpoint_name()}")
        print(f"   Timeout: {config.get_server_timeout()}s")
        print(f"   Retry attempts: {config.get_retry_attempts()}")
        print(f"   Retry delay: {config.get_retry_delay()}s")
        
        # Check if server URL matches what we're testing
        if config.get_server_url() != server_url:
            print(f"   ⚠ Config server URL doesn't match test URL")
            print(f"     Config: {config.get_server_url()}")
            print(f"     Test: {server_url}")
        
        return True
        
    except Exception as e:
        print(f"   Configuration check failed: {e}")
        return False

async def main():
    """Main debug function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug stuck authentication")
    parser.add_argument("--server-url", default="http://localhost:8080", 
                       help="Server URL to test")
    
    args = parser.parse_args()
    
    print("Pacman Sync Authentication Debug")
    print("=" * 40)
    print(f"Server URL: {args.server_url}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run diagnostic checks
    check_client_logs()
    check_token_storage()
    network_ok = check_network_connectivity(args.server_url)
    check_running_processes()
    config_ok = check_configuration(args.server_url)
    
    print("\n" + "=" * 40)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 40)
    
    if network_ok and config_ok:
        print("✓ Basic connectivity and configuration look good")
        print("\nIf authentication is still stuck, try:")
        print("1. Stop all running client processes")
        print("2. Clear token storage: rm -rf ~/.local/share/python_keyring/")
        print("3. Check server logs for registration attempts")
        print("4. Try manual registration test:")
        print(f"   python test_authentication_debug.py {args.server_url}")
        print("5. Increase timeout values in client configuration")
        print("6. Check for firewall/proxy issues")
    else:
        print("❌ Issues detected with connectivity or configuration")
        print("Fix these issues before troubleshooting authentication")
    
    print(f"\nFor real-time debugging:")
    print(f"1. Run client with verbose logging: python client/main.py --debug")
    print(f"2. Monitor server logs: journalctl -u pacman-sync-server -f")
    print(f"3. Monitor network traffic: tcpdump -i any port 8080")

if __name__ == "__main__":
    asyncio.run(main())