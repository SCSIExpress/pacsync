"""
Configuration Management for Pacman Sync Utility Client.

This module handles client configuration including server URL, authentication,
and endpoint settings with support for configuration files and environment variables.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from configparser import ConfigParser

from shared.interfaces import IConfigurationManager

logger = logging.getLogger(__name__)


class ClientConfiguration(IConfigurationManager):
    """
    Configuration manager for the Pacman Sync Utility client.
    
    Supports configuration from:
    1. Command line arguments (highest priority)
    2. Environment variables
    3. Configuration file
    4. Default values (lowest priority)
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self._config_file = config_file or self._get_default_config_path()
        self._config_data: Dict[str, Any] = {}
        self._overrides: Dict[str, Any] = {}
        
        # Load configuration
        self._load_configuration()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        # Use simplified user config directory: ~/.pacsync/client.conf
        config_dir = Path.home() / '.pacsync'
        config_dir.mkdir(parents=True, exist_ok=True)
        user_config_path = str(config_dir / 'client.conf')
        
        # If no user config exists, try to copy from system template or create default
        if not os.path.exists(user_config_path):
            # Check for system templates (for migration from existing installations)
            template_paths = [
                "/etc/pacman-sync/client/client.conf",
                "/etc/pacman-sync-utility/client.conf",
                str(Path(__file__).parent.parent / "config" / "client.conf.template")
            ]
            
            template_copied = False
            for template_path in template_paths:
                if os.path.exists(template_path):
                    try:
                        import shutil
                        shutil.copy2(template_path, user_config_path)
                        logger.info(f"Copied configuration template from {template_path} to {user_config_path}")
                        template_copied = True
                        break
                    except Exception as e:
                        logger.warning(f"Failed to copy config template from {template_path}: {e}")
            
            # If no template was found, create a minimal default config
            if not template_copied:
                self._create_default_config(user_config_path)
        
        return user_config_path
    
    def _create_default_config(self, config_path: str) -> None:
        """Create a minimal default configuration file."""
        try:
            default_config = """# Pacman Sync Utility Client Configuration
# Configuration file: {config_path}

[server]
# Server URL (required)
url = http://localhost:8080

# Connection timeout in seconds
timeout = 30

# Retry attempts for failed requests
retry_attempts = 3

[client]
# Endpoint name (defaults to hostname if not specified)
endpoint_name = {default_endpoint_name}

# Enable automatic synchronization
auto_sync = false

# Status update interval in seconds
update_interval = 300

[ui]
# Show desktop notifications
show_notifications = true

# Minimize to system tray on startup
minimize_to_tray = true

[operations]
# Confirm destructive operations
confirm_destructive_operations = true

[logging]
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
log_level = INFO
""".format(
                config_path=config_path,
                default_endpoint_name=self._get_default_endpoint_name()
            )
            
            with open(config_path, 'w') as f:
                f.write(default_config)
            
            logger.info(f"Created default configuration file: {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to create default configuration: {e}")
            raise
    
    def _load_configuration(self) -> None:
        """Load configuration from file and environment variables."""
        # Load from configuration file
        if os.path.exists(self._config_file):
            try:
                self._load_from_file()
                logger.info(f"Configuration loaded from: {self._config_file}")
            except Exception as e:
                logger.warning(f"Failed to load configuration file: {e}")
        else:
            logger.info(f"Configuration file not found: {self._config_file}")
        
        # Load from environment variables
        self._load_from_environment()
        
        # Set defaults for missing values
        self._set_defaults()
    
    def _load_from_file(self) -> None:
        """Load configuration from INI file."""
        config = ConfigParser()
        config.read(self._config_file)
        
        # Convert ConfigParser to dictionary
        for section_name in config.sections():
            section_data = {}
            for key, value in config[section_name].items():
                # Try to parse as JSON for complex values
                try:
                    section_data[key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    # Keep as string if not valid JSON
                    section_data[key] = value
            
            self._config_data[section_name] = section_data
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            'PACMAN_SYNC_SERVER_URL': ('server', 'url'),
            'PACMAN_SYNC_API_KEY': ('server', 'api_key'),
            'PACMAN_SYNC_ENDPOINT_NAME': ('client', 'endpoint_name'),
            'PACMAN_SYNC_POOL_ID': ('client', 'pool_id'),
            'PACMAN_SYNC_AUTO_SYNC': ('client', 'auto_sync'),
            'PACMAN_SYNC_UPDATE_INTERVAL': ('client', 'update_interval'),
            'PACMAN_SYNC_LOG_LEVEL': ('logging', 'level'),
            'PACMAN_SYNC_SHOW_NOTIFICATIONS': ('ui', 'show_notifications'),
            'PACMAN_SYNC_MINIMIZE_TO_TRAY': ('ui', 'minimize_to_tray'),
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                if section not in self._config_data:
                    self._config_data[section] = {}
                
                # Convert boolean strings
                if value.lower() in ('true', 'false'):
                    self._config_data[section][key] = value.lower() == 'true'
                # Convert numeric strings
                elif value.isdigit():
                    self._config_data[section][key] = int(value)
                else:
                    self._config_data[section][key] = value
    
    def _set_defaults(self) -> None:
        """Set default configuration values."""
        defaults = {
            'server': {
                'url': 'http://localhost:8080',
                'api_key': None,
                'timeout': 30.0,
                'retry_attempts': 3,
                'retry_delay': 1.0
            },
            'client': {
                'endpoint_name': self._get_default_endpoint_name(),
                'pool_id': None,
                'auto_sync': False,
                'update_interval': 300,  # 5 minutes
                'offline_queue_size': 100
            },
            'ui': {
                'show_notifications': True,
                'minimize_to_tray': True,
                'notification_timeout': 5000
            },
            'logging': {
                'level': 'INFO',
                'file': None,
                'max_size': 10485760,  # 10MB
                'backup_count': 3
            },
            'pacman': {
                'command': 'pacman',
                'sudo_command': 'sudo',
                'config_file': '/etc/pacman.conf'
            }
        }
        
        # Merge defaults with existing configuration
        for section, section_defaults in defaults.items():
            if section not in self._config_data:
                self._config_data[section] = {}
            
            for key, default_value in section_defaults.items():
                if key not in self._config_data[section]:
                    self._config_data[section][key] = default_value
    
    def _get_default_endpoint_name(self) -> str:
        """Generate default endpoint name."""
        import socket
        hostname = socket.gethostname()
        username = os.environ.get('USER', 'unknown')
        return f"{username}@{hostname}"
    
    def get_server_url(self) -> str:
        """Get server URL."""
        return self._overrides.get('server_url') or self._config_data['server']['url']
    
    def get_api_key(self) -> Optional[str]:
        """Get API key."""
        return self._overrides.get('api_key') or self._config_data['server'].get('api_key')
    
    def get_endpoint_name(self) -> str:
        """Get endpoint name."""
        return self._overrides.get('endpoint_name') or self._config_data['client']['endpoint_name']
    
    def get_hostname(self) -> str:
        """Get hostname."""
        import socket
        return socket.gethostname()
    
    def get_pool_id(self) -> Optional[str]:
        """Get assigned pool ID."""
        return self._overrides.get('pool_id') or self._config_data['client'].get('pool_id')
    
    def set_pool_id(self, pool_id: Optional[str]) -> None:
        """
        Set pool ID (typically from server assignment).
        
        Args:
            pool_id: Pool ID assigned by server (None to clear)
        """
        if pool_id:
            self._overrides['pool_id'] = pool_id
            logger.info(f"Pool ID updated to: {pool_id}")
        else:
            self._overrides.pop('pool_id', None)
            logger.info("Pool ID cleared")
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key in format 'section.key'
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if '.' not in key:
            return self._config_data.get(key, default)
        
        section, config_key = key.split('.', 1)
        section_data = self._config_data.get(section, {})
        
        if '.' in config_key:
            # Handle nested keys
            parts = config_key.split('.')
            current = section_data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default
            return current
        else:
            return section_data.get(config_key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            key: Configuration key in format 'section.key'
            value: Value to set
        """
        if '.' not in key:
            self._config_data[key] = value
            return
        
        section, config_key = key.split('.', 1)
        if section not in self._config_data:
            self._config_data[section] = {}
        
        if '.' in config_key:
            # Handle nested keys
            parts = config_key.split('.')
            current = self._config_data[section]
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            self._config_data[section][config_key] = value
    
    def set_override(self, key: str, value: Any) -> None:
        """
        Set configuration override (highest priority).
        
        Args:
            key: Configuration key
            value: Override value
        """
        self._overrides[key] = value
    
    def save_configuration(self) -> None:
        """Save current configuration to file."""
        try:
            # Check if current config file is writable
            if not self._is_config_writable():
                # If system config is not writable, save to user config
                user_config_path = self._get_user_config_path()
                logger.info(f"System config not writable, saving to user config: {user_config_path}")
                self._config_file = user_config_path
            
            config = ConfigParser()
            
            # Convert dictionary back to ConfigParser format
            for section_name, section_data in self._config_data.items():
                config.add_section(section_name)
                for key, value in section_data.items():
                    if isinstance(value, (dict, list)):
                        # Serialize complex values as JSON
                        config.set(section_name, key, json.dumps(value))
                    else:
                        config.set(section_name, key, str(value))
            
            # Ensure directory exists
            config_path = Path(self._config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write configuration file
            with open(self._config_file, 'w') as f:
                config.write(f)
            
            logger.info(f"Configuration saved to: {self._config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def _is_config_writable(self) -> bool:
        """Check if the current configuration file is writable."""
        try:
            if os.path.exists(self._config_file):
                return os.access(self._config_file, os.W_OK)
            else:
                # Check if parent directory is writable
                parent_dir = Path(self._config_file).parent
                return parent_dir.exists() and os.access(parent_dir, os.W_OK)
        except Exception:
            return False
    
    def _get_user_config_path(self) -> str:
        """Get user-specific configuration file path."""
        config_dir = Path.home() / '.pacsync'
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / 'client.conf')
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration data."""
        return self._config_data.copy()
    
    def get_config_file_path(self) -> str:
        """Get configuration file path."""
        return self._config_file
    
    def reload_configuration(self) -> None:
        """Reload configuration from file and environment."""
        self._config_data.clear()
        self._load_configuration()
        logger.info("Configuration reloaded")
    
    # Convenience methods for common configuration values
    
    def get_server_timeout(self) -> float:
        """Get server request timeout."""
        return self.get_config('server.timeout', 30.0)
    
    def get_debug_mode(self) -> bool:
        """Get debug mode setting."""
        return self.get_config('advanced.debug_mode', False)
    
    def get_structured_logging(self) -> bool:
        """Get structured logging setting."""
        return self.get_config('logging.structured_logging', False)
    
    def get_retry_attempts(self) -> int:
        """Get retry attempts setting."""
        return self.get_config('server.retry_attempts', 3)
    
    def get_retry_delay(self) -> float:
        """Get retry delay setting."""
        return self.get_config('server.retry_delay', 5.0)
    
    def get_update_interval(self) -> int:
        """Get status update interval."""
        return self.get_config('client.update_interval', 300)
    
    def get_log_file(self) -> Optional[str]:
        """Get log file path."""
        return self.get_config('logging.log_file')
    
    def get_quiet_mode(self) -> bool:
        """Get quiet mode setting."""
        return self.get_config('logging.quiet_mode', False)
    
    def get_retry_attempts(self) -> int:
        """Get number of retry attempts."""
        return self.get_config('server.retry_attempts', 3)
    
    def get_retry_delay(self) -> float:
        """Get retry delay."""
        return self.get_config('server.retry_delay', 1.0)
    
    def get_update_interval(self) -> int:
        """Get status update interval in seconds."""
        return self.get_config('client.update_interval', 300)
    
    def is_auto_sync_enabled(self) -> bool:
        """Check if auto-sync is enabled."""
        return self.get_config('client.auto_sync', False)
    
    def should_show_notifications(self) -> bool:
        """Check if notifications should be shown."""
        return self.get_config('ui.show_notifications', True)
    
    def should_minimize_to_tray(self) -> bool:
        """Check if application should minimize to tray."""
        return self.get_config('ui.minimize_to_tray', True)
    
    def get_notification_timeout(self) -> int:
        """Get notification timeout in milliseconds."""
        return self.get_config('ui.notification_timeout', 5000)
    
    def get_log_level(self) -> str:
        """Get logging level."""
        return self.get_config('logging.level', 'INFO')
    
    def get_log_file(self) -> Optional[str]:
        """Get log file path."""
        return self.get_config('logging.file')
    
    def get_pacman_command(self) -> str:
        """Get pacman command."""
        return self.get_config('pacman.command', 'pacman')
    
    def get_sudo_command(self) -> str:
        """Get sudo command."""
        return self.get_config('pacman.sudo_command', 'sudo')
    
    def get_pacman_config_file(self) -> str:
        """Get pacman configuration file path."""
        return self.get_config('pacman.config_file', '/etc/pacman.conf')