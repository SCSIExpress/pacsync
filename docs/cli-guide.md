# Command Line Interface Guide

This guide covers the command-line interface (CLI) for the Pacman Sync Utility, enabling automation and scripting capabilities.

## Overview

The CLI provides full access to all client functionality without requiring a graphical interface. This is essential for:
- **Server Administration**: Managing headless systems
- **Automation Scripts**: Integrating with deployment pipelines
- **Remote Management**: Operating over SSH connections
- **Batch Operations**: Processing multiple systems simultaneously

## Basic Usage

### Command Structure

```bash
python -m client.main [OPTIONS] [COMMAND] [ARGUMENTS]
```

### Global Options

```bash
--config PATH          # Use specific configuration file
--profile NAME         # Use named configuration profile
--server URL           # Override server URL
--api-key KEY          # Override API key
--debug                # Enable debug output
--verbose              # Increase output verbosity
--quiet                # Suppress non-error output
--no-color             # Disable colored output
--timeout SECONDS      # Set operation timeout
--help                 # Show help information
```

## Core Commands

### Status Operations

#### Check Sync Status
```bash
# Basic status check
python -m client.main --status

# Detailed status with package information
python -m client.main --status --detailed

# JSON output for scripting
python -m client.main --status --format json

# Check specific aspects
python -m client.main --status --check connectivity
python -m client.main --status --check packages
python -m client.main --status --check pool
```

**Example Output:**
```
Endpoint: workstation-01
Pool: development-pool
Status: Behind (23 packages)
Last Sync: 2 hours ago
Server: Connected (http://server:8080)

Package Summary:
  Total Packages: 1,247
  Packages Behind: 23
  Packages Ahead: 0
  Excluded: 15

Recent Activity:
  2024-01-15 14:30 - Sync completed successfully
  2024-01-15 12:15 - Set as latest by workstation-02
  2024-01-15 10:45 - Pool target updated
```

### Synchronization Commands

#### Sync to Latest
```bash
# Basic sync operation
python -m client.main --sync

# Dry run (show what would be done)
python -m client.main --sync --dry-run

# Force sync (ignore conflicts)
python -m client.main --sync --force

# Sync with confirmation prompt
python -m client.main --sync --confirm

# Sync specific packages only
python -m client.main --sync --packages firefox,chromium,git

# Exclude packages from sync
python -m client.main --sync --exclude linux,nvidia-dkms
```

#### Set as Latest
```bash
# Set current state as pool target
python -m client.main --set-latest

# Set with description
python -m client.main --set-latest --message "Updated development tools"

# Set specific packages as latest
python -m client.main --set-latest --packages firefox,chromium

# Dry run to preview changes
python -m client.main --set-latest --dry-run
```

#### Revert to Previous
```bash
# Revert to previous state
python -m client.main --revert

# Revert to specific state ID
python -m client.main --revert --state-id abc123

# Revert with confirmation
python -m client.main --revert --confirm

# Dry run revert
python -m client.main --revert --dry-run
```

### Package Management

#### List Packages
```bash
# List all packages
python -m client.main --packages

# List packages with status
python -m client.main --packages --status

# List only packages that need updates
python -m client.main --packages --filter behind

# List packages in specific repository
python -m client.main --packages --repo core

# Search for specific packages
python -m client.main --packages --search firefox

# Export package list
python -m client.main --packages --export packages.json
```

#### Package Information
```bash
# Get detailed package information
python -m client.main --package-info firefox

# Compare package versions
python -m client.main --package-compare firefox

# Show package dependencies
python -m client.main --package-deps firefox --recursive
```

## Advanced Commands

### Configuration Management

#### Configuration Operations
```bash
# Validate configuration
python -m client.main --check-config

# Show current configuration
python -m client.main --show-config

# Set configuration values
python -m client.main --set-config ui.show_notifications=false

# Reset configuration to defaults
python -m client.main --reset-config

# Export configuration
python -m client.main --export-config config-backup.ini
```

#### Profile Management
```bash
# List available profiles
python -m client.main --list-profiles

# Create new profile
python -m client.main --create-profile production

# Copy profile
python -m client.main --copy-profile dev production

# Delete profile
python -m client.main --delete-profile old-profile
```

### System Integration

#### Service Management
```bash
# Install systemd service
python -m client.main --install-service

# Uninstall systemd service
python -m client.main --uninstall-service

# Check service status
python -m client.main --service-status

# Restart service
python -m client.main --restart-service
```

#### WayBar Integration
```bash
# Output status for WayBar
python -m client.main --waybar-status

# WayBar with custom format
python -m client.main --waybar-status --format custom

# WayBar click handler
python -m client.main --waybar-click left
```

### Diagnostic Commands

#### Connection Testing
```bash
# Test server connectivity
python -m client.main --test-connection

# Test API authentication
python -m client.main --test-auth

# Test all components
python -m client.main --test-all

# Network diagnostics
python -m client.main --diagnose network
```

#### System Diagnostics
```bash
# Check system requirements
python -m client.main --check-requirements

# Test pacman integration
python -m client.main --test-pacman

# Test Qt/GUI components
python -m client.main --test-gui

# Generate diagnostic report
python -m client.main --diagnose --report diagnostic-report.txt
```

## Automation and Scripting

### Exit Codes

The CLI uses standard exit codes for script integration:

```bash
0   # Success
1   # General error
2   # Configuration error
3   # Network/connection error
4   # Sync conflict requiring manual resolution
5   # Permission/authentication error
6   # Package manager error
7   # System requirement not met
```

### Scripting Examples

#### Basic Sync Script
```bash
#!/bin/bash
# sync-system.sh - Basic synchronization script

set -e  # Exit on error

echo "Checking system status..."
if ! python -m client.main --status --quiet; then
    echo "Error: Cannot determine system status"
    exit 1
fi

echo "Starting synchronization..."
if python -m client.main --sync --quiet; then
    echo "Synchronization completed successfully"
    exit 0
else
    echo "Synchronization failed"
    exit 1
fi
```

#### Advanced Sync with Conflict Handling
```bash
#!/bin/bash
# advanced-sync.sh - Sync with conflict resolution

CONFIG_FILE="/etc/pacman-sync/client.conf"
LOG_FILE="/var/log/pacman-sync/sync.log"

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check if sync is needed
if python -m client.main --config "$CONFIG_FILE" --status --format json | jq -r '.status' | grep -q "in_sync"; then
    log "System is already in sync, no action needed"
    exit 0
fi

# Attempt sync with dry run first
log "Performing dry run to check for conflicts..."
if ! python -m client.main --config "$CONFIG_FILE" --sync --dry-run --quiet; then
    log "Dry run failed, manual intervention required"
    exit 4
fi

# Perform actual sync
log "Starting synchronization..."
if python -m client.main --config "$CONFIG_FILE" --sync --quiet; then
    log "Synchronization completed successfully"
    
    # Send notification (optional)
    if command -v notify-send >/dev/null; then
        notify-send "Pacman Sync" "System synchronized successfully"
    fi
    
    exit 0
else
    log "Synchronization failed"
    exit 1
fi
```

#### Batch Operations Script
```bash
#!/bin/bash
# batch-sync.sh - Sync multiple systems

SYSTEMS=(
    "workstation-01:192.168.1.10"
    "workstation-02:192.168.1.11"
    "server-01:192.168.1.20"
)

for system in "${SYSTEMS[@]}"; do
    name="${system%%:*}"
    ip="${system##*:}"
    
    echo "Syncing $name ($ip)..."
    
    if ssh "$ip" "python -m client.main --sync --quiet"; then
        echo "✓ $name synchronized successfully"
    else
        echo "✗ $name synchronization failed"
    fi
done
```

### Cron Integration

#### Scheduled Synchronization
```bash
# Add to crontab (crontab -e)

# Sync every hour
0 * * * * /usr/bin/python -m client.main --sync --quiet

# Check status every 15 minutes
*/15 * * * * /usr/bin/python -m client.main --status --quiet

# Daily system report
0 8 * * * /usr/bin/python -m client.main --status --detailed > /tmp/daily-sync-report.txt
```

#### Maintenance Tasks
```bash
# Weekly configuration backup
0 2 * * 0 /usr/bin/python -m client.main --export-config /backup/client-config-$(date +\%Y\%m\%d).ini

# Monthly diagnostic report
0 3 1 * * /usr/bin/python -m client.main --diagnose --report /var/log/pacman-sync/monthly-diagnostic-$(date +\%Y\%m).txt
```

## Output Formats

### Standard Output
Default human-readable format:
```bash
python -m client.main --status
```

### JSON Output
Machine-readable JSON format:
```bash
python -m client.main --status --format json
```

**Example JSON Output:**
```json
{
    "endpoint_name": "workstation-01",
    "pool_id": "development-pool",
    "status": "behind",
    "packages": {
        "total": 1247,
        "behind": 23,
        "ahead": 0,
        "excluded": 15
    },
    "last_sync": "2024-01-15T14:30:00Z",
    "server": {
        "url": "http://server:8080",
        "connected": true,
        "last_seen": "2024-01-15T16:45:00Z"
    }
}
```

### CSV Output
Tabular data format:
```bash
python -m client.main --packages --format csv
```

### Custom Formats
Template-based custom output:
```bash
python -m client.main --status --format template --template "Status: {{status}} | Packages: {{packages.total}}"
```

## Environment Variables

### Configuration Override
```bash
export PACMAN_SYNC_SERVER="http://server:8080"
export PACMAN_SYNC_API_KEY="your-api-key"
export PACMAN_SYNC_POOL="production-pool"
export PACMAN_SYNC_DEBUG="true"

python -m client.main --status
```

### Automation Variables
```bash
export PACMAN_SYNC_QUIET="true"        # Suppress output
export PACMAN_SYNC_NO_CONFIRM="true"   # Skip confirmations
export PACMAN_SYNC_TIMEOUT="300"       # Set timeout
export PACMAN_SYNC_LOG_LEVEL="ERROR"   # Set log level
```

## Integration Examples

### CI/CD Pipeline Integration

#### GitLab CI Example
```yaml
# .gitlab-ci.yml
sync_packages:
  stage: deploy
  script:
    - python -m client.main --sync --quiet
  only:
    - main
  tags:
    - arch-linux
```

#### GitHub Actions Example
```yaml
# .github/workflows/sync.yml
name: Sync Packages
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  sync:
    runs-on: self-hosted
    steps:
      - name: Sync packages
        run: python -m client.main --sync --quiet
```

### Monitoring Integration

#### Nagios Check
```bash
#!/bin/bash
# check_pacman_sync.sh - Nagios check script

STATUS=$(python -m client.main --status --format json | jq -r '.status')

case "$STATUS" in
    "in_sync")
        echo "OK - System is in sync"
        exit 0
        ;;
    "behind")
        echo "WARNING - System is behind pool target"
        exit 1
        ;;
    "ahead")
        echo "WARNING - System is ahead of pool target"
        exit 1
        ;;
    "error")
        echo "CRITICAL - Sync system error"
        exit 2
        ;;
    *)
        echo "UNKNOWN - Cannot determine sync status"
        exit 3
        ;;
esac
```

#### Prometheus Metrics
```bash
#!/bin/bash
# pacman-sync-metrics.sh - Generate Prometheus metrics

STATUS_JSON=$(python -m client.main --status --format json)

echo "# HELP pacman_sync_status Current sync status (0=in_sync, 1=behind, 2=ahead, 3=error)"
echo "# TYPE pacman_sync_status gauge"
echo "pacman_sync_status $(echo "$STATUS_JSON" | jq -r '.status_code')"

echo "# HELP pacman_sync_packages_total Total number of packages"
echo "# TYPE pacman_sync_packages_total gauge"
echo "pacman_sync_packages_total $(echo "$STATUS_JSON" | jq -r '.packages.total')"

echo "# HELP pacman_sync_packages_behind Number of packages behind"
echo "# TYPE pacman_sync_packages_behind gauge"
echo "pacman_sync_packages_behind $(echo "$STATUS_JSON" | jq -r '.packages.behind')"
```

## Troubleshooting CLI Issues

### Common Problems

#### Command Not Found
```bash
# Ensure Python module path is correct
python -c "import client.main; print('Module found')"

# Use full path if needed
python /opt/pacman-sync/client/main.py --status
```

#### Permission Errors
```bash
# Check sudo configuration for pacman
sudo -l | grep pacman

# Test pacman access
sudo pacman -Q | head -5
```

#### Configuration Issues
```bash
# Validate configuration
python -m client.main --check-config --verbose

# Show effective configuration
python -m client.main --show-config --include-defaults
```

### Debug Mode

Enable comprehensive debugging:
```bash
# Full debug output
python -m client.main --debug --verbose --status

# Debug specific components
python -m client.main --debug --component api --status
python -m client.main --debug --component pacman --sync
```

## Best Practices

### Script Development
- **Always check exit codes** in scripts
- **Use `--quiet` flag** for automated operations
- **Implement proper error handling** for all scenarios
- **Log operations** for audit trails
- **Test scripts** in dry-run mode first

### Security
- **Protect API keys** in scripts and environment variables
- **Use configuration files** with proper permissions (600)
- **Validate inputs** in custom scripts
- **Audit script access** regularly

### Performance
- **Use JSON output** for parsing in scripts
- **Cache status information** when possible
- **Batch operations** when working with multiple systems
- **Set appropriate timeouts** for network operations

## Getting Help

### Built-in Help
```bash
# General help
python -m client.main --help

# Command-specific help
python -m client.main --sync --help
python -m client.main --status --help

# List all available commands
python -m client.main --list-commands
```

### Diagnostic Information
```bash
# Generate comprehensive diagnostic report
python -m client.main --diagnose --full --report diagnostic.txt

# Test all components
python -m client.main --test-all --verbose
```

## Next Steps

After mastering the CLI:

1. Explore [API Documentation](api-documentation.md) for direct API access
2. Set up [Monitoring Integration](troubleshooting.md#monitoring) 
3. Review [Advanced Configuration](configuration.md) for optimization
4. Check [Desktop Client Guide](desktop-client-guide.md) for GUI features