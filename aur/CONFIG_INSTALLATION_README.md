# Configuration File Installation Implementation

This document describes the implementation of task 4.2 "Implement configuration file installation" for the AUR packaging specification.

## Overview

The configuration file installation system provides:

1. **Configuration Directory Structure**: Creates `/etc/pacman-sync-utility/` with proper permissions
2. **File Permissions and Ownership**: Ensures all configuration files have correct permissions (644) and ownership (root:root)
3. **Backup and Restore**: Handles `.pacnew`/`.pacsave` files through pacman's backup system
4. **Validation**: Provides tools to validate configuration file integrity
5. **Management Utilities**: Includes scripts for backup, restore, and merge operations

## Implementation Details

### Directory Structure

The implementation creates the following directory structure:

```
/etc/pacman-sync-utility/
├── client.conf          # Client configuration (backed up by pacman)
├── server.conf          # Server configuration (backed up by pacman)  
├── pools.conf           # Pool definitions (backed up by pacman)
├── jwt-secret           # JWT secret key (600 permissions, pacman-sync:pacman-sync)
└── conf.d/              # Additional configuration files directory
```

### Configuration Files

#### client.conf
- **Purpose**: Client application configuration
- **Permissions**: 644 (root:root)
- **Backup**: Managed by pacman backup system
- **Format**: YAML format with comprehensive client settings

#### server.conf  
- **Purpose**: Server application configuration
- **Permissions**: 644 (root:root)
- **Backup**: Managed by pacman backup system
- **Format**: YAML format with server, database, and security settings

#### pools.conf
- **Purpose**: Pool definitions and assignment rules
- **Permissions**: 644 (root:root)
- **Backup**: Managed by pacman backup system
- **Format**: YAML format with pool configurations

### PKGBUILD Integration

The PKGBUILD includes the following configuration-related elements:

```bash
# Configuration files in source array
source=(
    # ... other sources ...
    "client.conf"
    "server.conf"
    "pools.conf"
    "validate-config-installation.py"
    "config-backup-restore.sh"
)

# Backup arrays for each package
backup=('etc/pacman-sync-utility/client.conf'
        'etc/pacman-sync-utility/server.conf'
        'etc/pacman-sync-utility/pools.conf')

# Configuration installation in _install_common_files()
install -dm755 "$pkgdir/etc/$pkgbase"
install -dm755 "$pkgdir/etc/$pkgbase/conf.d"
install -Dm644 "$srcdir/client.conf" "$pkgdir/etc/$pkgbase/client.conf"
install -Dm644 "$srcdir/server.conf" "$pkgdir/etc/$pkgbase/server.conf"
install -Dm644 "$srcdir/pools.conf" "$pkgdir/etc/$pkgbase/pools.conf"
```

### Install Script Integration

The `pacman-sync-utility.install` script handles:

#### post_install()
- Creates configuration directory with proper permissions
- Sets file ownership and permissions
- Generates JWT secret key
- Updates server configuration with generated secret
- Validates configuration files
- Provides user guidance

#### post_upgrade()
- Updates directory and file permissions
- Handles JWT secret key for upgrades
- Checks for `.pacnew` files and notifies user
- Runs database migrations
- Restarts services if needed

#### post_remove()
- Checks for `.pacsave` files and notifies user
- Provides cleanup instructions
- Preserves user data by default

### Management Utilities

#### pacman-sync-validate-config
- **Location**: `/usr/bin/pacman-sync-validate-config`
- **Purpose**: Validates configuration file syntax and structure
- **Features**:
  - YAML and INI format validation
  - File permission checking
  - Directory structure validation
  - Comprehensive error reporting

#### pacman-sync-config-backup
- **Location**: `/usr/bin/pacman-sync-config-backup`
- **Purpose**: Configuration backup and restore operations
- **Commands**:
  - `backup`: Create timestamped backup
  - `restore`: Restore from latest backup
  - `merge`: Interactive merge of `.pacnew` files
  - `check`: Check for `.pacnew`/`.pacsave` files
  - `list`: List available backups

### Backup and Restore System

#### Pacman Integration
- Uses pacman's built-in backup system via `backup=()` arrays
- Automatically creates `.pacnew` files for modified configurations during upgrades
- Creates `.pacsave` files when package is removed

#### Manual Backup System
- Timestamped backups in `/var/backups/pacman-sync-utility/config/`
- Backup metadata with creation date, hostname, and package version
- Interactive restore with current configuration backup

#### .pacnew/.pacsave Handling
- Automatic detection during upgrades and removals
- User notification about available files
- Interactive merge tool using vimdiff
- Backup creation before merge operations

### File Permissions and Security

#### Configuration Files
- **Mode**: 644 (readable by all, writable by root)
- **Owner**: root:root
- **Purpose**: Standard system configuration files

#### JWT Secret File
- **Mode**: 600 (readable/writable by owner only)
- **Owner**: pacman-sync:pacman-sync
- **Purpose**: Sensitive authentication key

#### Directories
- **Mode**: 755 (accessible by all, writable by root)
- **Owner**: root:root
- **Purpose**: Standard system directories

### Validation and Testing

#### Configuration Validation
- Syntax checking for YAML and INI formats
- Structure validation for required sections
- Permission and ownership verification
- Directory structure validation

#### Test Suite
- Comprehensive test coverage for all functionality
- Temporary test environment creation
- File permission and ownership testing
- PKGBUILD and install script integration testing
- Backup and restore functionality testing

## Usage Examples

### Installation
```bash
# Install package (automatically sets up configuration)
yay -S pacman-sync-utility

# Validate configuration after installation
pacman-sync-validate-config
```

### Configuration Management
```bash
# Create backup before making changes
pacman-sync-config-backup backup

# Check for .pacnew files after upgrade
pacman-sync-config-backup check

# Interactively merge .pacnew files
pacman-sync-config-backup merge

# Restore from backup if needed
pacman-sync-config-backup restore
```

### Manual Configuration
```bash
# Edit configuration files
sudo nano /etc/pacman-sync-utility/client.conf
sudo nano /etc/pacman-sync-utility/server.conf
sudo nano /etc/pacman-sync-utility/pools.conf

# Validate changes
pacman-sync-validate-config
```

## Requirements Compliance

This implementation satisfies all requirements from the specification:

### Requirement 6.1 ✓
- **Requirement**: Create default configuration files in /etc/pacman-sync-utility/
- **Implementation**: PKGBUILD installs client.conf, server.conf, and pools.conf with proper defaults

### Requirement 6.2 ✓  
- **Requirement**: Preserve existing configuration files during updates
- **Implementation**: Uses pacman backup system with backup=() arrays

### Requirement 6.3 ✓
- **Requirement**: Create .pacnew files for new configurations during updates
- **Implementation**: Pacman automatically creates .pacnew files for modified backed-up files

### Requirement 6.4 ✓
- **Requirement**: Preserve user configuration files as .pacsave during removal
- **Implementation**: Pacman automatically creates .pacsave files when removing backed-up files

## Files Modified/Created

### Modified Files
- `aur/PKGBUILD`: Added configuration file sources, backup arrays, and installation logic
- `aur/pacman-sync-utility.install`: Added configuration handling in all install functions

### Created Files
- `aur/validate-config-installation.py`: Configuration validation utility
- `aur/config-backup-restore.sh`: Backup and restore management script
- `aur/test-config-installation.py`: Comprehensive test suite
- `aur/CONFIG_INSTALLATION_README.md`: This documentation file

### Existing Configuration Files
- `aur/client.conf`: Client configuration template
- `aur/server.conf`: Server configuration template  
- `aur/pools.conf`: Pool definitions template

## Testing

Run the test suite to verify implementation:

```bash
python3 aur/test-config-installation.py
```

Expected output: All 7 tests should pass, confirming proper implementation of configuration file installation functionality.