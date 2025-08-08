# Desktop Client Guide

This guide covers how to use the Pacman Sync Utility desktop client for daily package synchronization tasks.

## Getting Started

### First Launch

After installation, the client will:
1. Appear as an icon in your system tray
2. Automatically register with the configured server
3. Join the default pool (if configured)
4. Begin monitoring package state

### System Tray Icon

The system tray icon indicates your current sync status:

- **🟢 Green Circle**: In sync with pool target state
- **🔵 Blue Arrow Up**: Your system is ahead (has newer packages)
- **🔴 Red Arrow Down**: Your system is behind (has older packages)
- **🟡 Yellow Sync**: Synchronization in progress
- **⚠️ Warning Triangle**: Error or attention needed
- **⚫ Gray Circle**: Offline or disconnected

### Context Menu

Right-click the system tray icon to access:

- **Sync to Latest**: Update packages to match pool target
- **Set as Latest**: Make your current state the pool target
- **Revert to Previous**: Restore previous package state
- **Show Status**: Display detailed status window
- **Settings**: Open configuration dialog
- **About**: Version and system information
- **Quit**: Exit the application

## Daily Operations

### Synchronizing Packages

#### Sync to Latest
This updates your system to match the pool's target state:

1. Right-click the system tray icon
2. Select **"Sync to Latest"**
3. Review the changes in the confirmation dialog:
   - **Packages to Install**: New packages to be added
   - **Packages to Upgrade**: Existing packages to be updated
   - **Packages to Remove**: Packages to be uninstalled
4. Click **"Proceed"** to start synchronization
5. Monitor progress in the progress dialog
6. Review results when complete

#### Set as Latest
This makes your current package state the target for the entire pool:

1. Ensure your system has the desired package configuration
2. Right-click the system tray icon
3. Select **"Set as Latest"**
4. Confirm the action in the dialog
5. All other endpoints in your pool will be notified of the new target state

#### Revert to Previous
This restores your system to the previous synchronized state:

1. Right-click the system tray icon
2. Select **"Revert to Previous"**
3. Review what will be changed in the confirmation dialog
4. Click **"Revert"** to proceed
5. Monitor the restoration process

### Status Monitoring

#### Status Window
Click **"Show Status"** to view detailed information:

**System Information**
- Endpoint name and pool assignment
- Current sync status and last update time
- System architecture and pacman version

**Package Summary**
- Total packages installed
- Packages ahead of pool target
- Packages behind pool target
- Excluded packages

**Recent Activity**
- Last synchronization operation
- Recent package changes
- Error messages or warnings

#### Notifications

The client shows desktop notifications for:
- **Sync Complete**: When synchronization finishes successfully
- **New Target State**: When another endpoint sets a new target
- **Sync Required**: When your system falls behind the target
- **Errors**: When operations fail or need attention

You can configure notification settings in the preferences.

## Advanced Features

### Package Details

#### Viewing Package Information
1. Open the status window
2. Click on **"Package Details"** tab
3. Browse or search for specific packages
4. View detailed information:
   - Current version vs. target version
   - Repository source
   - Installation size and dependencies
   - Last update time

#### Package Exclusions
Some packages are automatically excluded from synchronization:
- **System Critical**: Kernel, bootloader, drivers
- **Hardware Specific**: Graphics drivers, firmware
- **User Configured**: Packages you've manually excluded

To manage exclusions:
1. Open **Settings** → **Sync Options**
2. Navigate to **Package Exclusions**
3. Add or remove packages from the exclusion list

### Conflict Resolution

When package conflicts occur, the client will:

1. **Display Conflict Dialog**: Show conflicting packages and versions
2. **Provide Resolution Options**:
   - **Use Pool Target**: Accept the pool's target version
   - **Keep Current**: Keep your current version
   - **Manual Selection**: Choose specific versions
3. **Apply Resolution**: Execute the chosen resolution strategy

#### Automatic Conflict Resolution
Configure automatic resolution in settings:
- **Always Use Pool Target**: Automatically accept pool versions
- **Always Keep Current**: Keep your versions when conflicts occur
- **Prompt for Decision**: Always ask for manual resolution

### Offline Operation

The client handles network disconnections gracefully:

#### Offline Capabilities
- **Status Monitoring**: Continue monitoring local package state
- **Queue Operations**: Queue sync operations for when connection returns
- **Local History**: Access previous states stored locally
- **Configuration**: Modify settings without server connection

#### Reconnection Behavior
When connection is restored:
- **Automatic Reconnection**: Client automatically reconnects to server
- **Status Synchronization**: Upload current status to server
- **Pending Operations**: Execute any queued operations
- **Conflict Resolution**: Handle any conflicts that occurred while offline

## Configuration

### Client Settings

Access settings through the system tray context menu or by running:
```bash
python -m client.main --settings
```

#### General Settings
- **Endpoint Name**: Unique identifier for this client
- **Server URL**: Address of the central server
- **Pool Assignment**: Which pool this endpoint belongs to
- **Auto-sync**: Enable automatic synchronization

#### User Interface Settings
- **Show Notifications**: Enable desktop notifications
- **Minimize to Tray**: Start minimized to system tray
- **Update Interval**: How often to check for status updates
- **Theme**: UI theme (system, light, dark)

#### Synchronization Settings
- **Excluded Packages**: Packages to never synchronize
- **Excluded Repositories**: Repositories to ignore
- **Conflict Resolution**: Default strategy for handling conflicts
- **Backup Database**: Create backups before major changes

#### Advanced Settings
- **Debug Mode**: Enable detailed logging
- **Custom Pacman Path**: Non-standard pacman installation
- **AUR Support**: Enable AUR package synchronization
- **Connection Timeout**: Network timeout settings

### Profile Management

#### Multiple Profiles
Create different configuration profiles for different scenarios:

```bash
# Work profile
python -m client.main --profile work

# Home profile  
python -m client.main --profile home

# Development profile
python -m client.main --profile dev
```

#### Profile Configuration
Each profile can have different:
- Server connections
- Pool assignments
- Sync policies
- UI preferences

## Command Line Interface

### Basic Commands

The client supports command-line operation for automation:

```bash
# Check current status
python -m client.main --status

# Sync to latest state
python -m client.main --sync

# Set current state as latest
python -m client.main --set-latest

# Revert to previous state
python -m client.main --revert

# Show detailed package information
python -m client.main --packages

# Test server connection
python -m client.main --test-connection
```

### Advanced Commands

```bash
# Dry run (show what would be done)
python -m client.main --sync --dry-run

# Force sync (ignore conflicts)
python -m client.main --sync --force

# Sync specific packages only
python -m client.main --sync --packages firefox,chromium

# Exclude packages from sync
python -m client.main --sync --exclude linux,nvidia

# Use specific configuration file
python -m client.main --config /path/to/config.conf --status

# Enable debug output
python -m client.main --debug --sync
```

### Exit Codes

The CLI returns standard exit codes:
- **0**: Success
- **1**: General error
- **2**: Configuration error
- **3**: Network error
- **4**: Sync conflict
- **5**: Permission error

## Integration

### WayBar Integration

For WayBar users, the client provides JSON output:

#### WayBar Configuration
Add to your WayBar config:
```json
{
    "custom/pacman-sync": {
        "exec": "python -m client.main --waybar-status",
        "return-type": "json",
        "interval": 30,
        "on-click": "python -m client.main --sync",
        "on-click-right": "python -m client.main --settings"
    }
}
```

#### Status Output Format
```json
{
    "text": "📦 In Sync",
    "tooltip": "Pool: development\nPackages: 1247\nLast sync: 2 minutes ago",
    "class": "in-sync",
    "percentage": 100
}
```

### Systemd Integration

#### User Service
The client runs as a user systemd service:

```bash
# Check service status
systemctl --user status pacman-sync-client

# Start/stop service
systemctl --user start pacman-sync-client
systemctl --user stop pacman-sync-client

# Enable/disable auto-start
systemctl --user enable pacman-sync-client
systemctl --user disable pacman-sync-client

# View logs
journalctl --user -u pacman-sync-client -f
```

#### Service Configuration
Customize the service by editing:
`~/.config/systemd/user/pacman-sync-client.service`

### Desktop Environment Integration

#### Autostart
The client can be configured to start automatically:

1. **GNOME/KDE**: Use the desktop environment's startup applications
2. **Systemd**: Enable the user service
3. **Manual**: Add to your shell's startup scripts

#### Desktop Notifications
The client integrates with your desktop's notification system:
- **GNOME**: Uses libnotify
- **KDE**: Uses KNotifications
- **Others**: Falls back to Qt notifications

## Troubleshooting

### Common Issues

#### System Tray Icon Not Visible
1. **Check Desktop Environment Support**:
   ```bash
   python -m client.qt.application --test-tray
   ```
2. **Install Required Packages**:
   ```bash
   sudo pacman -S libappindicator-gtk3
   ```
3. **Run Without Tray**:
   ```bash
   python -m client.main --no-tray
   ```

#### Cannot Connect to Server
1. **Test Network Connectivity**:
   ```bash
   curl http://your-server:8080/health/live
   ```
2. **Check Configuration**:
   ```bash
   python -m client.main --check-config
   ```
3. **Verify API Key**:
   ```bash
   python -m client.api_client --test-auth
   ```

#### Sync Operations Fail
1. **Check Pacman Access**:
   ```bash
   python -m client.pacman_interface --test
   ```
2. **Verify Permissions**:
   ```bash
   # Client needs sudo access for pacman
   sudo -v
   ```
3. **Review Logs**:
   ```bash
   python -m client.main --debug --sync
   ```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Run with debug output
python -m client.main --debug

# Save debug log to file
python -m client.main --debug --log-file debug.log

# Enable all debug categories
python -m client.main --debug --verbose
```

### Log Files

Client logs are stored in:
- **User Log**: `~/.local/share/pacman-sync/client.log`
- **Debug Log**: `~/.local/share/pacman-sync/debug.log`
- **Systemd Journal**: `journalctl --user -u pacman-sync-client`

## Best Practices

### Daily Usage
- **Monitor Status**: Check the system tray icon regularly
- **Review Changes**: Always review changes before confirming sync operations
- **Keep Backups**: Enable database backups before major changes
- **Update Regularly**: Keep the client software updated

### System Maintenance
- **Clean Logs**: Regularly clean old log files
- **Update Configuration**: Keep configuration current with server changes
- **Test Connectivity**: Periodically test server connectivity
- **Review Exclusions**: Update package exclusions as needed

### Security
- **Protect API Keys**: Keep API keys secure and rotate them regularly
- **Use HTTPS**: Configure server with HTTPS for production use
- **Monitor Access**: Review client access logs on the server
- **Update Software**: Keep both client and server software updated

## Getting Help

If you encounter issues with the desktop client:

1. **Check Status**: Use `--status` command to check current state
2. **Review Logs**: Check client logs for error messages
3. **Test Components**: Use built-in test commands
4. **Consult Documentation**: Review [Troubleshooting Guide](troubleshooting.md)
5. **Report Issues**: Create detailed bug reports with log output

## Next Steps

After mastering the desktop client:

1. Explore [Web UI Management](web-ui-guide.md) for advanced pool management
2. Set up [API Integration](api-documentation.md) for automation
3. Configure [WayBar Integration](waybar_integration.md) for status bar display
4. Review [Advanced Configuration](configuration.md) options