# Systemd Service Files for Pacman Sync Utility

This directory contains systemd service files for the Pacman Sync Utility AUR package.

## Service Files

### User Services (installed to `/usr/lib/systemd/user/`)

#### `pacman-sync-client.service`
Main client service that runs in user session with graphical environment support.

**Features:**
- Graphical session integration with proper dependencies
- Environment variables for X11 and Wayland support
- Qt application environment configuration
- Robust restart policies with failure handling
- Security hardening appropriate for user services
- Resource limits to prevent excessive resource usage

**Usage:**
```bash
# Enable and start for current user
systemctl --user enable --now pacman-sync-client.service

# Check status
systemctl --user status pacman-sync-client.service

# View logs
journalctl --user -u pacman-sync-client.service
```

#### `pacman-sync-client-tray.service`
Dedicated system tray service that can run independently or alongside the main client.

**Features:**
- Binds to main client service
- Optimized for system tray functionality
- Lower resource limits for tray-only operation
- Faster restart times for UI responsiveness

**Usage:**
```bash
# Enable tray service (automatically enabled with main service)
systemctl --user enable pacman-sync-client-tray.service

# Start tray only
systemctl --user start pacman-sync-client-tray.service
```

#### `pacman-sync-client@.service`
Template service for running multiple client instances.

**Features:**
- Instance-specific configuration support
- Per-instance environment variables
- Support for multiple display configurations
- Isolated configuration directories

**Usage:**
```bash
# Start instance for display :1
systemctl --user start pacman-sync-client@1.service

# Enable instance for user ID 1000
systemctl --user enable pacman-sync-client@1000.service
```

### System Services (installed to `/usr/lib/systemd/system/`)

#### `pacman-sync-server.service`
System-wide server service (see separate documentation).

## Configuration

### Service Overrides

Users can customize service behavior by creating override files:

```bash
# Create override directory
mkdir -p ~/.config/systemd/user/pacman-sync-client.service.d/

# Create override file
cat > ~/.config/systemd/user/pacman-sync-client.service.d/override.conf << EOF
[Service]
Environment=PACMAN_SYNC_LOG_LEVEL=DEBUG
MemoryMax=1G
EOF

# Reload systemd configuration
systemctl --user daemon-reload
```

### Environment Variables

The service files set the following environment variables:

- `DISPLAY`: X11 display server connection
- `QT_QPA_PLATFORM`: Qt platform abstraction (xcb for X11)
- `XDG_RUNTIME_DIR`: Runtime directory for user session
- `WAYLAND_DISPLAY`: Wayland display server connection
- `QT_WAYLAND_DISABLE_WINDOWDECORATION`: Wayland window decoration
- `QT_AUTO_SCREEN_SCALE_FACTOR`: Automatic DPI scaling
- `QT_SCALE_FACTOR_ROUNDING_POLICY`: DPI scaling rounding policy

## Security Features

All user services include security hardening:

- `NoNewPrivileges=yes`: Prevents privilege escalation
- `PrivateTmp=yes`: Private temporary directory
- `ProtectSystem=strict`: Read-only system directories
- `ProtectHome=read-only`: Read-only home directory access
- `RestrictNamespaces=yes`: Restrict namespace creation
- `RestrictRealtime=yes`: Prevent realtime scheduling
- `RestrictSUIDSGID=yes`: Prevent SUID/SGID execution
- `RemoveIPC=yes`: Clean up IPC objects on exit

## Resource Limits

Default resource limits are configured to prevent excessive resource usage:

- **Main Client Service**: 512MB memory, 100 tasks
- **Tray Service**: 256MB memory, 50 tasks
- **Template Service**: 512MB memory, 100 tasks

## Troubleshooting

### Service Won't Start

1. Check service status:
   ```bash
   systemctl --user status pacman-sync-client.service
   ```

2. Check logs:
   ```bash
   journalctl --user -u pacman-sync-client.service -f
   ```

3. Verify graphical session:
   ```bash
   systemctl --user status graphical-session.target
   ```

### Environment Issues

1. Check environment variables:
   ```bash
   systemctl --user show-environment
   ```

2. Test display connection:
   ```bash
   echo $DISPLAY
   xdpyinfo  # For X11
   ```

### Permission Issues

1. Check file permissions:
   ```bash
   ls -la /usr/bin/pacman-sync-client
   ```

2. Verify user service directory:
   ```bash
   ls -la ~/.config/systemd/user/
   ```

## Validation

Use the included validation script to verify service file integrity:

```bash
cd aur/
./validate-systemd-client-service.sh
```

This script checks:
- Service file syntax and structure
- Required sections and keys
- Graphical session dependencies
- Environment variable configuration
- Restart policies
- Security settings
- Resource limits