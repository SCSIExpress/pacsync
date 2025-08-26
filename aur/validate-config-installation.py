#!/usr/bin/env python3
"""
Configuration Installation Validation Script
Validates configuration files during AUR package installation
"""

import os
import sys
import yaml
import configparser
from pathlib import Path


def validate_yaml_config(config_path):
    """Validate YAML configuration file"""
    try:
        with open(config_path, 'r') as f:
            yaml.safe_load(f)
        return True, None
    except yaml.YAMLError as e:
        return False, f"YAML syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"


def validate_ini_config(config_path):
    """Validate INI configuration file"""
    try:
        config = configparser.ConfigParser()
        config.read(config_path)
        return True, None
    except configparser.Error as e:
        return False, f"INI syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"


def validate_client_config(config_path):
    """Validate client configuration file"""
    if not os.path.exists(config_path):
        return False, "Client configuration file not found"
    
    # Try YAML first, then INI
    is_valid, error = validate_yaml_config(config_path)
    if not is_valid:
        is_valid, error = validate_ini_config(config_path)
    
    if not is_valid:
        return False, f"Client config validation failed: {error}"
    
    return True, None


def validate_server_config(config_path):
    """Validate server configuration file"""
    if not os.path.exists(config_path):
        return False, "Server configuration file not found"
    
    # Try YAML first, then INI
    is_valid, error = validate_yaml_config(config_path)
    if not is_valid:
        is_valid, error = validate_ini_config(config_path)
    
    if not is_valid:
        return False, f"Server config validation failed: {error}"
    
    return True, None


def validate_pools_config(config_path):
    """Validate pools configuration file"""
    if not os.path.exists(config_path):
        return False, "Pools configuration file not found"
    
    is_valid, error = validate_yaml_config(config_path)
    if not is_valid:
        return False, f"Pools config validation failed: {error}"
    
    return True, None


def check_file_permissions(config_path, expected_mode=0o644):
    """Check file permissions"""
    try:
        stat_info = os.stat(config_path)
        actual_mode = stat_info.st_mode & 0o777
        
        if actual_mode != expected_mode:
            return False, f"Incorrect permissions: {oct(actual_mode)}, expected: {oct(expected_mode)}"
        
        return True, None
    except Exception as e:
        return False, f"Error checking permissions: {e}"


def check_directory_structure(config_dir):
    """Check configuration directory structure"""
    config_path = Path(config_dir)
    
    # Check main directory exists
    if not config_path.exists():
        return False, f"Configuration directory does not exist: {config_dir}"
    
    if not config_path.is_dir():
        return False, f"Configuration path is not a directory: {config_dir}"
    
    # Check conf.d subdirectory
    conf_d_path = config_path / "conf.d"
    if not conf_d_path.exists():
        return False, f"conf.d subdirectory does not exist: {conf_d_path}"
    
    if not conf_d_path.is_dir():
        return False, f"conf.d path is not a directory: {conf_d_path}"
    
    return True, None


def main():
    """Main validation function"""
    config_dir = "/etc/pacman-sync-utility"
    
    print("Validating configuration installation...")
    
    # Check directory structure
    is_valid, error = check_directory_structure(config_dir)
    if not is_valid:
        print(f"ERROR: Directory structure validation failed: {error}")
        return 1
    
    print("✓ Configuration directory structure is valid")
    
    # Validate configuration files
    config_files = {
        "client.conf": validate_client_config,
        "server.conf": validate_server_config,
        "pools.conf": validate_pools_config
    }
    
    all_valid = True
    
    for filename, validator in config_files.items():
        config_path = os.path.join(config_dir, filename)
        
        is_valid, error = validator(config_path)
        if not is_valid:
            print(f"ERROR: {filename} validation failed: {error}")
            all_valid = False
            continue
        
        # Check file permissions
        is_valid, error = check_file_permissions(config_path)
        if not is_valid:
            print(f"WARNING: {filename} permission issue: {error}")
            # Don't fail on permission issues, just warn
        
        print(f"✓ {filename} is valid")
    
    if not all_valid:
        print("\nConfiguration validation failed!")
        return 1
    
    print("\n✓ All configuration files are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())