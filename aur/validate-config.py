#!/usr/bin/env python3
"""
Configuration validation script for Pacman Sync Utility AUR package.
This script validates configuration files and handles default value setup.
"""

import os
import sys
import yaml
import secrets
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional


class ConfigValidator:
    """Validates and processes configuration files for AUR installation."""
    
    def __init__(self, config_dir: str = "/etc/pacman-sync-utility"):
        self.config_dir = Path(config_dir)
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_server_config(self, config_path: Optional[Path] = None) -> bool:
        """Validate server configuration file."""
        if config_path is None:
            config_path = self.config_dir / "server.conf"
        
        if not config_path.exists():
            self.errors.append(f"Server config file not found: {config_path}")
            return False
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Validate required sections
            required_sections = ['server', 'security', 'paths']
            for section in required_sections:
                if section not in config:
                    self.errors.append(f"Missing required section '{section}' in server config")
            
            # Validate server section
            if 'server' in config:
                server_config = config['server']
                
                # Validate host and port
                if 'host' not in server_config:
                    self.errors.append("Missing 'host' in server configuration")
                if 'port' not in server_config:
                    self.errors.append("Missing 'port' in server configuration")
                elif not isinstance(server_config['port'], int) or not (1 <= server_config['port'] <= 65535):
                    self.errors.append("Invalid port number in server configuration")
                
                # Validate database URL
                if 'database_url' not in server_config:
                    self.errors.append("Missing 'database_url' in server configuration")
                
                # Validate log level
                valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                if 'log_level' in server_config and server_config['log_level'] not in valid_log_levels:
                    self.errors.append(f"Invalid log_level. Must be one of: {', '.join(valid_log_levels)}")
            
            # Validate security section
            if 'security' in config:
                security_config = config['security']
                
                # Check JWT secret key
                if 'jwt_secret_key' not in security_config:
                    self.errors.append("Missing 'jwt_secret_key' in security configuration")
                elif security_config['jwt_secret_key'] == 'CHANGE_THIS_SECRET_KEY_ON_INSTALL':
                    self.warnings.append("JWT secret key should be changed from default value")
                
                # Validate token expiry
                if 'token_expiry' in security_config:
                    if not isinstance(security_config['token_expiry'], int) or security_config['token_expiry'] <= 0:
                        self.errors.append("Invalid token_expiry. Must be a positive integer")
            
            # Validate paths section
            if 'paths' in config:
                paths_config = config['paths']
                
                # Check required paths
                required_paths = ['data_dir', 'log_dir', 'config_dir']
                for path_key in required_paths:
                    if path_key not in paths_config:
                        self.errors.append(f"Missing '{path_key}' in paths configuration")
            
            return len(self.errors) == 0
            
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in server config: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error validating server config: {e}")
            return False
    
    def validate_client_config(self, config_path: Optional[Path] = None) -> bool:
        """Validate client configuration file."""
        if config_path is None:
            config_path = self.config_dir / "client.conf"
        
        if not config_path.exists():
            self.errors.append(f"Client config file not found: {config_path}")
            return False
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Validate required sections
            required_sections = ['client', 'server']
            for section in required_sections:
                if section not in config:
                    self.errors.append(f"Missing required section '{section}' in client config")
            
            # Validate client section
            if 'client' in config:
                client_config = config['client']
                
                # Validate server URL
                if 'server_url' not in client_config:
                    self.errors.append("Missing 'server_url' in client configuration")
                elif not client_config['server_url'].startswith(('http://', 'https://')):
                    self.errors.append("Invalid server_url format. Must start with http:// or https://")
                
                # Validate update interval
                if 'update_interval' in client_config:
                    if not isinstance(client_config['update_interval'], int) or client_config['update_interval'] <= 0:
                        self.errors.append("Invalid update_interval. Must be a positive integer")
            
            # Validate server section
            if 'server' in config:
                server_config = config['server']
                
                # Validate timeout
                if 'timeout' in server_config:
                    if not isinstance(server_config['timeout'], int) or server_config['timeout'] <= 0:
                        self.errors.append("Invalid timeout. Must be a positive integer")
                
                # Validate retry attempts
                if 'retry_attempts' in server_config:
                    if not isinstance(server_config['retry_attempts'], int) or server_config['retry_attempts'] < 0:
                        self.errors.append("Invalid retry_attempts. Must be a non-negative integer")
            
            # Validate logging section if present
            if 'logging' in config:
                logging_config = config['logging']
                
                valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                if 'log_level' in logging_config and logging_config['log_level'] not in valid_log_levels:
                    self.errors.append(f"Invalid log_level. Must be one of: {', '.join(valid_log_levels)}")
            
            return len(self.errors) == 0
            
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in client config: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error validating client config: {e}")
            return False
    
    def validate_pools_config(self, config_path: Optional[Path] = None) -> bool:
        """Validate pools configuration file."""
        if config_path is None:
            config_path = self.config_dir / "pools.conf"
        
        if not config_path.exists():
            self.warnings.append(f"Pools config file not found: {config_path} (optional)")
            return True  # Pools config is optional
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Validate pool definitions
            if config:
                for pool_name, pool_config in config.items():
                    if pool_name in ['assignment_rules', 'global']:
                        continue  # Skip special sections
                    
                    if not isinstance(pool_config, dict):
                        self.errors.append(f"Pool '{pool_name}' configuration must be a dictionary")
                        continue
                    
                    # Validate required pool fields
                    required_fields = ['name', 'description']
                    for field in required_fields:
                        if field not in pool_config:
                            self.errors.append(f"Missing '{field}' in pool '{pool_name}'")
                    
                    # Validate max_endpoints
                    if 'max_endpoints' in pool_config:
                        if not isinstance(pool_config['max_endpoints'], int) or pool_config['max_endpoints'] <= 0:
                            self.errors.append(f"Invalid max_endpoints in pool '{pool_name}'. Must be a positive integer")
                    
                    # Validate sync_strategy
                    if 'sync_strategy' in pool_config:
                        valid_strategies = ['latest', 'conservative', 'performance', 'minimal', 'manual']
                        if pool_config['sync_strategy'] not in valid_strategies:
                            self.errors.append(f"Invalid sync_strategy in pool '{pool_name}'. Must be one of: {', '.join(valid_strategies)}")
            
            return len(self.errors) == 0
            
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in pools config: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error validating pools config: {e}")
            return False
    
    def generate_jwt_secret(self, config_path: Optional[Path] = None) -> bool:
        """Generate a secure JWT secret key and update server configuration."""
        if config_path is None:
            config_path = self.config_dir / "server.conf"
        
        try:
            # Generate a secure random key
            jwt_secret = secrets.token_hex(32)
            
            # Read current config
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Replace the placeholder with the generated secret
            updated_content = content.replace(
                'jwt_secret_key: "CHANGE_THIS_SECRET_KEY_ON_INSTALL"',
                f'jwt_secret_key: "{jwt_secret}"'
            )
            
            # Write back the updated config
            with open(config_path, 'w') as f:
                f.write(updated_content)
            
            print(f"Generated JWT secret key for {config_path}")
            return True
            
        except Exception as e:
            self.errors.append(f"Error generating JWT secret: {e}")
            return False
    
    def create_directories(self) -> bool:
        """Create necessary directories with proper permissions."""
        directories = [
            ("/var/lib/pacman-sync-utility", 0o755),
            ("/var/lib/pacman-sync-utility/database", 0o755),
            ("/var/lib/pacman-sync-utility/logs", 0o755),
            ("/var/log/pacman-sync-utility", 0o755),
        ]
        
        try:
            for dir_path, mode in directories:
                Path(dir_path).mkdir(parents=True, exist_ok=True, mode=mode)
                print(f"Created directory: {dir_path}")
            return True
        except Exception as e:
            self.errors.append(f"Error creating directories: {e}")
            return False
    
    def validate_all(self) -> bool:
        """Validate all configuration files."""
        print(f"Validating configuration files in {self.config_dir}")
        
        server_valid = self.validate_server_config()
        client_valid = self.validate_client_config()
        pools_valid = self.validate_pools_config()
        
        return server_valid and client_valid and pools_valid
    
    def print_results(self):
        """Print validation results."""
        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print("\nConfiguration validation passed!")


def main():
    parser = argparse.ArgumentParser(description="Validate Pacman Sync Utility configuration files")
    parser.add_argument("--config-dir", default="/etc/pacman-sync-utility",
                       help="Configuration directory path")
    parser.add_argument("--generate-jwt", action="store_true",
                       help="Generate JWT secret key")
    parser.add_argument("--create-dirs", action="store_true",
                       help="Create necessary directories")
    parser.add_argument("--setup", action="store_true",
                       help="Perform full setup (generate JWT, create dirs, validate)")
    
    args = parser.parse_args()
    
    validator = ConfigValidator(args.config_dir)
    
    success = True
    
    if args.setup or args.create_dirs:
        if not validator.create_directories():
            success = False
    
    if args.setup or args.generate_jwt:
        if not validator.generate_jwt_secret():
            success = False
    
    if not validator.validate_all():
        success = False
    
    validator.print_results()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()