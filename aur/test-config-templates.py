#!/usr/bin/env python3
"""
Test script to validate configuration templates for AUR packaging.
This script ensures the configuration templates are valid and complete.
"""

import yaml
import sys
from pathlib import Path


def test_yaml_validity(file_path: Path) -> bool:
    """Test if a YAML file is valid."""
    try:
        with open(file_path, 'r') as f:
            yaml.safe_load(f)
        print(f"✓ {file_path.name}: Valid YAML")
        return True
    except yaml.YAMLError as e:
        print(f"✗ {file_path.name}: Invalid YAML - {e}")
        return False
    except Exception as e:
        print(f"✗ {file_path.name}: Error reading file - {e}")
        return False


def test_server_config_structure(file_path: Path) -> bool:
    """Test server configuration structure."""
    try:
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f)
        
        required_sections = ['server', 'security', 'database', 'features', 'paths', 'monitoring', 'performance']
        missing_sections = []
        
        for section in required_sections:
            if section not in config:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"✗ {file_path.name}: Missing sections: {', '.join(missing_sections)}")
            return False
        
        # Check critical settings
        if 'jwt_secret_key' not in config['security']:
            print(f"✗ {file_path.name}: Missing jwt_secret_key in security section")
            return False
        
        if 'database_url' not in config['server']:
            print(f"✗ {file_path.name}: Missing database_url in server section")
            return False
        
        print(f"✓ {file_path.name}: Valid server configuration structure")
        return True
        
    except Exception as e:
        print(f"✗ {file_path.name}: Error validating structure - {e}")
        return False


def test_client_config_structure(file_path: Path) -> bool:
    """Test client configuration structure."""
    try:
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f)
        
        required_sections = ['client', 'server', 'gui', 'operations', 'pacman', 'logging']
        missing_sections = []
        
        for section in required_sections:
            if section not in config:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"✗ {file_path.name}: Missing sections: {', '.join(missing_sections)}")
            return False
        
        # Check critical settings
        if 'server_url' not in config['client']:
            print(f"✗ {file_path.name}: Missing server_url in client section")
            return False
        
        if 'pacman_path' not in config['pacman']:
            print(f"✗ {file_path.name}: Missing pacman_path in pacman section")
            return False
        
        print(f"✓ {file_path.name}: Valid client configuration structure")
        return True
        
    except Exception as e:
        print(f"✗ {file_path.name}: Error validating structure - {e}")
        return False


def test_pools_config_structure(file_path: Path) -> bool:
    """Test pools configuration structure."""
    try:
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check if default pool exists
        if 'default' not in config:
            print(f"✗ {file_path.name}: Missing default pool definition")
            return False
        
        # Check default pool structure
        default_pool = config['default']
        required_fields = ['name', 'description', 'auto_assign', 'max_endpoints', 'sync_strategy']
        missing_fields = []
        
        for field in required_fields:
            if field not in default_pool:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"✗ {file_path.name}: Missing fields in default pool: {', '.join(missing_fields)}")
            return False
        
        # Check global section if present
        if 'global' in config:
            global_config = config['global']
            if 'default_sync_strategy' not in global_config:
                print(f"✗ {file_path.name}: Missing default_sync_strategy in global section")
                return False
        
        print(f"✓ {file_path.name}: Valid pools configuration structure")
        return True
        
    except Exception as e:
        print(f"✗ {file_path.name}: Error validating structure - {e}")
        return False


def main():
    """Main test function."""
    print("Testing AUR configuration templates...")
    print("=" * 50)
    
    aur_dir = Path("aur")
    if not aur_dir.exists():
        print("✗ AUR directory not found")
        sys.exit(1)
    
    all_tests_passed = True
    
    # Test server configuration
    server_config = aur_dir / "server.conf"
    if server_config.exists():
        if not test_yaml_validity(server_config):
            all_tests_passed = False
        elif not test_server_config_structure(server_config):
            all_tests_passed = False
    else:
        print("✗ server.conf not found")
        all_tests_passed = False
    
    # Test client configuration
    client_config = aur_dir / "client.conf"
    if client_config.exists():
        if not test_yaml_validity(client_config):
            all_tests_passed = False
        elif not test_client_config_structure(client_config):
            all_tests_passed = False
    else:
        print("✗ client.conf not found")
        all_tests_passed = False
    
    # Test pools configuration
    pools_config = aur_dir / "pools.conf"
    if pools_config.exists():
        if not test_yaml_validity(pools_config):
            all_tests_passed = False
        elif not test_pools_config_structure(pools_config):
            all_tests_passed = False
    else:
        print("✗ pools.conf not found")
        all_tests_passed = False
    
    print("=" * 50)
    if all_tests_passed:
        print("✓ All configuration template tests passed!")
        sys.exit(0)
    else:
        print("✗ Some configuration template tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()