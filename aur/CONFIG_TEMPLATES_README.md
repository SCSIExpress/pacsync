# Configuration Templates for AUR Package

This directory contains configuration templates for the Pacman Sync Utility AUR package. These templates are designed to be installed system-wide and provide sensible defaults for both server and client components.

## Files

### Configuration Templates

- **`server.conf`** - Server configuration template
- **`client.conf`** - Client configuration template  
- **`pools.conf`** - Pool definitions template

### Installation Scripts

- **`install-config.sh`** - Configuration installation script used by PKGBUILD
- **`validate-config.py`** - Configuration validation and setup script
- **`test-config-templates.py`** - Test script for validating template structure

## Installation Paths

When installed via the AUR package, configuration files are placed in:

- `/etc/pacman-sync-utility/server.conf` - System-wide server configuration
- `/etc/pacman-sync-utility/client.conf` - System-wide client configuration
- `/etc/pacman-sync-utility/pools.conf` - System-wide pool definitions

## User Configuration Override

Users can override system-wide settings by creating configuration files in:

- `~/.config/pacman-sync-utility/client.conf` - User-specific client configuration
- `~/.config/pacman-sync-utility/pools.conf` - User-specific pool definitions

User configurations are merged with system configurations, with user settings taking precedence.

## Configuration Format

All configuration files use YAML format with the following structure:

### Server Configuration (`server.conf`)

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  database_url: "sqlite:///var/lib/pacman-sync-utility/database/server.db"
  log_level: "INFO"
  log_file: "/var/lib/pacman-sync-utility/logs/server.log"

security:
  jwt_secret_key: "auto-generated-on-install"
  token_expiry: 3600

# ... additional sections
```

### Client Configuration (`client.conf`)

```yaml
client:
  server_url: "http://localhost:8000"
  endpoint_name: "auto-detect"
  pool_id: null
  update_interval: 300

gui:
  system_tray: true
  notifications: true
  auto_start: false

# ... additional sections
```

### Pools Configuration (`pools.conf`)

```yaml
default:
  name: "Default Pool"
  description: "Default pool for new endpoints"
  auto_assign: true
  max_endpoints: 50
  sync_strategy: "latest"

# ... additional pool definitions
```

## Configuration Validation

The package includes a configuration validator that:

1. Validates YAML syntax
2. Checks for required sections and fields
3. Validates data types and value ranges
4. Generates secure JWT secret keys
5. Creates necessary directories with proper permissions

### Running Validation

```bash
# Validate configuration files
pacman-sync-validate-config --config-dir /etc/pacman-sync-utility

# Perform full setup (generate JWT, create dirs, validate)
pacman-sync-validate-config --setup

# Generate JWT secret key only
pacman-sync-validate-config --generate-jwt
```

## Security Considerations

### JWT Secret Key

The server configuration includes a JWT secret key that is automatically generated during package installation. This key is used for endpoint authentication and should be:

- Kept secure and not shared
- Backed up before system upgrades
- Regenerated if compromised

### File Permissions

Configuration files are installed with the following permissions:

- Configuration files: `644` (readable by all, writable by root)
- Data directories: `755` (accessible by service user)
- Log files: `644` (readable by all, writable by service user)

### Service User

The server component runs as the `pacman-sync` system user, which is created during package installation. This user has minimal privileges and only access to:

- Configuration files (read-only)
- Data directory (`/var/lib/pacman-sync-utility/`)
- Log directory (`/var/lib/pacman-sync-utility/logs/`)

## Customization

### Server Configuration

Key settings to customize:

- `server.host` - Bind address (default: all interfaces)
- `server.port` - Server port (default: 8000)
- `server.database_url` - Database connection string
- `security.jwt_secret_key` - Authentication secret (auto-generated)
- `features.enable_repository_analysis` - Enable repo analysis

### Client Configuration

Key settings to customize:

- `client.server_url` - Server connection URL
- `client.endpoint_name` - Endpoint identifier
- `gui.system_tray` - Enable system tray integration
- `gui.notifications` - Enable desktop notifications
- `pacman.use_sudo` - Use sudo for pacman operations

### Pool Configuration

Key settings to customize:

- Pool definitions for organizing endpoints
- Assignment rules for automatic pool assignment
- Global settings for pool behavior

## Troubleshooting

### Configuration Validation Errors

If configuration validation fails:

1. Check YAML syntax using `yamllint`
2. Verify all required sections are present
3. Check data types and value ranges
4. Review file permissions

### Service Startup Issues

If services fail to start:

1. Check configuration file syntax
2. Verify database connectivity
3. Check file permissions and ownership
4. Review systemd service logs

### Permission Issues

If permission errors occur:

1. Verify service user exists (`pacman-sync`)
2. Check directory ownership and permissions
3. Ensure configuration files are readable
4. Review SELinux/AppArmor policies if applicable

## Testing

To test configuration templates during development:

```bash
# Test YAML validity and structure
./test-config-templates.py

# Validate configuration files
./validate-config.py --config-dir .

# Test installation script (requires root)
sudo ./install-config.sh .
```

## Integration with PKGBUILD

The configuration templates are integrated into the PKGBUILD through:

1. **prepare()** function - Validates templates during build
2. **package()** functions - Installs templates to appropriate locations
3. **post_install()** script - Runs configuration setup and validation
4. **post_upgrade()** script - Handles configuration updates

### PKGBUILD Integration Example

```bash
package() {
    # Install configuration templates
    install -Dm644 "$srcdir/server.conf" "$pkgdir/etc/pacman-sync-utility/server.conf"
    install -Dm644 "$srcdir/client.conf" "$pkgdir/etc/pacman-sync-utility/client.conf"
    install -Dm644 "$srcdir/pools.conf" "$pkgdir/etc/pacman-sync-utility/pools.conf"
    
    # Install configuration scripts
    install -Dm755 "$srcdir/validate-config.py" "$pkgdir/usr/bin/pacman-sync-validate-config"
    install -Dm755 "$srcdir/install-config.sh" "$pkgdir/usr/share/pacman-sync-utility/install-config.sh"
}
```

This ensures proper configuration management following Arch Linux packaging standards and provides a smooth user experience for AUR package installation and maintenance.