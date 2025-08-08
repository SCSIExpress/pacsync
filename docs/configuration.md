# Configuration Guide

This guide covers all configuration options for the Pacman Sync Utility server and client components.

## Configuration Overview

The system uses INI-style configuration files with environment variable overrides for containerized deployments.

### Configuration Files Location

- **Server**: `/etc/pacman-sync/server.conf` (system-wide) or `./server.conf` (local)
- **Client**: `~/.config/pacman-sync/client.conf` (user-specific)
- **Docker**: Environment variables override file-based configuration

## Server Configuration

### Basic Configuration

Create `/etc/pacman-sync/server.conf`:

```ini
[database]
# Database type: 'postgresql' or 'internal'
type = postgresql
# Connection URL for PostgreSQL
url = postgresql://username:password@localhost:5432/database_name
# For internal database, specify file path
# file = /var/lib/pacman-sync/database.db

[server]
# Server bind address
host = 0.0.0.0
# Server port
port = 8080
# Enable debug mode (development only)
debug = false
# Number of worker processes
workers = 4
# Request timeout in seconds
timeout = 30

[security]
# JWT secret key for authentication (generate with: openssl rand -hex 32)
jwt_secret_key = your-secret-key-here
# Token expiration time in hours
token_expiry = 24
# API rate limiting (requests per minute per IP)
api_rate_limit = 100
# Enable CORS for web UI
enable_cors = true
# Allowed origins for CORS
cors_origins = http://localhost:3000,https://your-domain.com

[features]
# Enable automatic repository analysis
enable_repository_analysis = true
# Automatically clean up old package states
auto_cleanup_old_states = true
# Maximum number of historical states to keep per pool
max_state_history = 50
# Enable real-time notifications
enable_notifications = true
# Sync operation timeout in minutes
sync_timeout = 30

[logging]
# Log level: DEBUG, INFO, WARNING, ERROR
level = INFO
# Log file path (empty for stdout)
file = /var/log/pacman-sync/server.log
# Maximum log file size in MB
max_size = 100
# Number of backup log files to keep
backup_count = 5
# Log format
format = %(asctime)s - %(name)s - %(levelname)s - %(message)s

[web_ui]
# Enable web UI
enabled = true
# Web UI static files path
static_path = /opt/pacman-sync/server/web/dist
# Web UI title
title = Pacman Sync Utility
# Theme: light, dark, auto
theme = auto
```

### Database Configuration Options

#### PostgreSQL Configuration

```ini
[database]
type = postgresql
url = postgresql://username:password@host:port/database
# Connection pool settings
pool_size = 10
max_overflow = 20
pool_timeout = 30
pool_recycle = 3600
```

#### Internal Database Configuration

```ini
[database]
type = internal
file = /var/lib/pacman-sync/database.db
# SQLite-specific options
timeout = 20
check_same_thread = false
```

### Environment Variable Overrides

For Docker deployments, use environment variables:

```bash
# Database configuration
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:pass@host:5432/db
DATABASE_POOL_SIZE=10

# Server configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
SERVER_DEBUG=false
SERVER_WORKERS=4

# Security configuration
JWT_SECRET_KEY=your-secret-key
TOKEN_EXPIRY=24
API_RATE_LIMIT=100

# Feature flags
ENABLE_REPOSITORY_ANALYSIS=true
AUTO_CLEANUP_OLD_STATES=true
MAX_STATE_HISTORY=50

# Logging configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/pacman-sync/server.log
```

## Client Configuration

### Basic Configuration

Create `~/.config/pacman-sync/client.conf`:

```ini
[server]
# Server URL
url = http://your-server:8080
# API authentication key
api_key = your-api-key
# Connection timeout in seconds
timeout = 30
# Retry attempts for failed requests
retry_attempts = 3
# Retry delay in seconds
retry_delay = 5

[client]
# Unique endpoint name for this client
endpoint_name = my-desktop
# Default pool ID to join
pool_id = default-pool
# Enable automatic synchronization
auto_sync = false
# Auto-sync interval in minutes
auto_sync_interval = 60
# Enable automatic pool joining
auto_join_pool = true

[ui]
# Show desktop notifications
show_notifications = true
# Minimize to system tray on startup
minimize_to_tray = true
# Status update interval in seconds
update_interval = 300
# UI theme: system, light, dark
theme = system
# Show detailed package information
show_package_details = true
# Enable sound notifications
enable_sounds = false

[pacman]
# Pacman configuration file path
config_path = /etc/pacman.conf
# Package cache directory
cache_dir = /var/cache/pacman/pkg
# Pacman command path
command = /usr/bin/pacman
# Enable AUR package support (requires yay or paru)
enable_aur = false
# AUR helper command
aur_helper = yay

[sync]
# Packages to exclude from synchronization
exclude_packages = linux,linux-headers,nvidia
# Repositories to exclude
exclude_repos = testing
# Conflict resolution strategy: manual, newest, oldest
conflict_resolution = manual
# Enable dry-run mode (show what would be done)
dry_run = false
# Backup package database before sync
backup_database = true

[waybar]
# Enable WayBar integration
enabled = false
# Update interval for WayBar in seconds
update_interval = 30
# WayBar output format: json, text
output_format = json
# Show package count in status
show_package_count = true

[logging]
# Log level: DEBUG, INFO, WARNING, ERROR
level = INFO
# Log file path (empty for stdout)
file = ~/.local/share/pacman-sync/client.log
# Maximum log file size in MB
max_size = 10
# Number of backup log files to keep
backup_count = 3
```

### Advanced Client Configuration

#### System Tray Configuration

```ini
[system_tray]
# System tray implementation: auto, appindicator, statusnotifier, qt
implementation = auto
# Tray icon theme
icon_theme = default
# Show tooltip with status information
show_tooltip = true
# Tooltip update interval in seconds
tooltip_update_interval = 60
# Context menu items to show
menu_items = sync,set_latest,revert,status,settings,quit
```

#### Qt Application Configuration

```ini
[qt]
# Qt application style
style = Fusion
# Enable high DPI scaling
enable_high_dpi = true
# Qt platform theme
platform_theme = gtk3
# Window flags for dialogs
dialog_flags = WindowStaysOnTopHint
# Enable native dialogs
use_native_dialogs = true
```

## Configuration Templates

### Production Server Configuration

```ini
[database]
type = postgresql
url = postgresql://pacman_sync:secure_password@db-server:5432/pacman_sync_prod
pool_size = 20
max_overflow = 30

[server]
host = 0.0.0.0
port = 8080
debug = false
workers = 8
timeout = 60

[security]
jwt_secret_key = your-production-secret-key-32-chars-long
token_expiry = 12
api_rate_limit = 200
enable_cors = true
cors_origins = https://your-domain.com

[features]
enable_repository_analysis = true
auto_cleanup_old_states = true
max_state_history = 100
sync_timeout = 45

[logging]
level = INFO
file = /var/log/pacman-sync/server.log
max_size = 500
backup_count = 10
```

### Development Server Configuration

```ini
[database]
type = internal
file = ./dev_database.db

[server]
host = 127.0.0.1
port = 8080
debug = true
workers = 1

[security]
jwt_secret_key = dev-secret-key-not-for-production
token_expiry = 168
api_rate_limit = 1000

[logging]
level = DEBUG
file = 
```

### Multi-Server Client Configuration

```ini
[server]
url = http://primary-server:8080
# Fallback servers
fallback_urls = http://backup-server:8080,http://tertiary-server:8080
api_key = your-api-key
timeout = 15
retry_attempts = 5

[client]
endpoint_name = workstation-01
pool_id = development-pool
auto_sync = true
auto_sync_interval = 30

[sync]
exclude_packages = linux,linux-headers,nvidia,nvidia-utils
conflict_resolution = newest
backup_database = true
```

## Configuration Validation

### Server Configuration Validation

```bash
# Validate server configuration
python3 -m server.main --check-config

# Test database connection
python3 -m server.database.connection --test

# Validate all settings
python3 -m server.config --validate
```

### Client Configuration Validation

```bash
# Validate client configuration
python3 -m client.main --check-config

# Test server connectivity
python3 -m client.api_client --test-connection

# Validate pacman integration
python3 -m client.pacman_interface --test
```

## Dynamic Configuration

### Runtime Configuration Changes

Some configuration options can be changed at runtime through the API:

```bash
# Update server settings
curl -X PUT http://server:8080/api/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"features.auto_cleanup_old_states": true}'

# Update client settings
python3 -m client.main --set-config ui.show_notifications=false
```

### Configuration Profiles

Create multiple configuration profiles for different environments:

```bash
# Server profiles
/etc/pacman-sync/server-production.conf
/etc/pacman-sync/server-staging.conf
/etc/pacman-sync/server-development.conf

# Client profiles
~/.config/pacman-sync/client-work.conf
~/.config/pacman-sync/client-home.conf

# Use specific profile
python3 -m server.main --config /etc/pacman-sync/server-production.conf
python3 -m client.main --config ~/.config/pacman-sync/client-work.conf
```

## Security Configuration

### Authentication Setup

1. **Generate JWT Secret Key**
   ```bash
   # Generate secure secret key
   openssl rand -hex 32
   ```

2. **API Key Management**
   ```bash
   # Generate API key for client
   python3 -m server.auth.generate_key --endpoint-name "my-desktop"
   
   # Revoke API key
   python3 -m server.auth.revoke_key --key-id "key-id"
   ```

3. **SSL/TLS Configuration**
   ```ini
   [server]
   # Enable HTTPS (requires reverse proxy)
   secure = true
   # Enforce secure cookies
   secure_cookies = true
   ```

### Rate Limiting Configuration

```ini
[security]
# Global rate limit
api_rate_limit = 100
# Per-endpoint rate limits
endpoint_rate_limits = sync:10,set_latest:5,revert:3
# Rate limit window in minutes
rate_limit_window = 1
# Enable rate limit headers
include_rate_limit_headers = true
```

## Monitoring Configuration

### Health Check Configuration

```ini
[health]
# Enable health check endpoints
enabled = true
# Health check interval in seconds
check_interval = 30
# Include detailed system information
include_system_info = true
# Database health check timeout
db_timeout = 5
```

### Metrics Configuration

```ini
[metrics]
# Enable Prometheus metrics
enabled = true
# Metrics endpoint path
endpoint = /metrics
# Include detailed metrics
detailed = true
# Metrics collection interval
interval = 15
```

## Troubleshooting Configuration

### Debug Configuration

```ini
[debug]
# Enable debug mode
enabled = true
# Debug log file
log_file = /tmp/pacman-sync-debug.log
# Include stack traces in errors
include_traces = true
# Enable request/response logging
log_requests = true
```

### Configuration Backup

```bash
# Backup current configuration
cp /etc/pacman-sync/server.conf /etc/pacman-sync/server.conf.backup
cp ~/.config/pacman-sync/client.conf ~/.config/pacman-sync/client.conf.backup

# Restore from backup
cp /etc/pacman-sync/server.conf.backup /etc/pacman-sync/server.conf
cp ~/.config/pacman-sync/client.conf.backup ~/.config/pacman-sync/client.conf
```

## Next Steps

After configuring your system:

1. Review the [Web UI Guide](web-ui-guide.md) for pool management
2. Check the [Desktop Client Guide](desktop-client-guide.md) for daily usage
3. Set up [API Documentation](api-documentation.md) for automation
4. Configure [WayBar Integration](waybar_integration.md) if needed