#!/usr/bin/env python3
"""
Test script for pacman-conf integration.

This script tests the updated pacman interface that uses pacman-conf
to get repository information with actual mirror URLs.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "client"))

from client.pacman_interface import PacmanInterface


def test_pacman_conf_availability():
    """Test if pacman-conf is available on the system."""
    print("🔍 Testing pacman-conf availability...")
    
    try:
        result = subprocess.run(["pacman-conf", "--version"], 
                              capture_output=True, text=True, check=True)
        print(f"✅ pacman-conf is available: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ pacman-conf failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ pacman-conf not found. Make sure pacman is installed.")
        return False


def test_repository_configuration():
    """Test repository configuration parsing."""
    print("\n🔧 Testing repository configuration...")
    
    try:
        pacman = PacmanInterface()
        config = pacman.config
        
        print(f"✅ Architecture: {config.architecture}")
        print(f"✅ Cache directory: {config.cache_dir}")
        print(f"✅ Database path: {config.db_path}")
        print(f"✅ Log file: {config.log_file}")
        
        print(f"\n📦 Found {len(config.repositories)} repository entries:")
        
        # Group by repository name to show mirrors
        repo_groups = {}
        for repo in config.repositories:
            name = repo["name"]
            if name not in repo_groups:
                repo_groups[name] = []
            repo_groups[name].append(repo["server"])
        
        for repo_name, servers in repo_groups.items():
            print(f"  {repo_name}:")
            for i, server in enumerate(servers):
                prefix = "    primary:" if i == 0 else "    mirror: "
                print(f"{prefix} {server}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to parse repository configuration: {e}")
        return False


def test_repository_mirrors():
    """Test repository mirror extraction."""
    print("\n🪞 Testing repository mirror extraction...")
    
    try:
        pacman = PacmanInterface()
        mirrors = pacman.get_repository_mirrors()
        
        print(f"✅ Found mirrors for {len(mirrors)} repositories:")
        
        for repo_name, mirror_list in mirrors.items():
            print(f"  {repo_name}: {len(mirror_list)} mirrors")
            for mirror in mirror_list[:3]:  # Show first 3 mirrors
                print(f"    - {mirror}")
            if len(mirror_list) > 3:
                print(f"    ... and {len(mirror_list) - 3} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to get repository mirrors: {e}")
        return False


def test_server_repository_info():
    """Test repository info formatted for server."""
    print("\n🖥️  Testing server repository info...")
    
    try:
        pacman = PacmanInterface()
        endpoint_id = "test-endpoint"
        repo_info = pacman.get_repository_info_for_server(endpoint_id)
        
        print(f"✅ Generated server info for {len(repo_info)} repositories:")
        
        for repo_name, info in repo_info.items():
            print(f"  {repo_name}:")
            print(f"    Primary URL: {info['primary_url']}")
            print(f"    Mirrors: {len(info['mirrors'])} total")
            print(f"    Architecture: {info['architecture']}")
            print(f"    Endpoint ID: {info['endpoint_id']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate server repository info: {e}")
        return False


def test_repository_list_command():
    """Test direct pacman-conf repository list command."""
    print("\n📋 Testing direct pacman-conf commands...")
    
    try:
        # Test repository list
        result = subprocess.run(["pacman-conf", "--repo-list"], 
                              capture_output=True, text=True, check=True)
        repos = result.stdout.strip().split('\n')
        print(f"✅ Repository list: {', '.join(repos)}")
        
        # Test getting servers for first repository
        if repos and repos[0]:
            first_repo = repos[0]
            server_result = subprocess.run(["pacman-conf", "--repo", first_repo, "Server"], 
                                         capture_output=True, text=True, check=True)
            servers = server_result.stdout.strip().split('\n')
            print(f"✅ Servers for {first_repo}: {len(servers)} found")
            for server in servers[:2]:  # Show first 2
                print(f"    - {server}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ pacman-conf command failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing pacman-conf commands: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Pacman-conf Integration Test")
    print("=" * 50)
    
    tests = [
        test_pacman_conf_availability,
        test_repository_configuration,
        test_repository_mirrors,
        test_server_repository_info,
        test_repository_list_command
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! pacman-conf integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())