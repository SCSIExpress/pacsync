# Pacman Sync Utility - AUR Package

This directory contains the AUR (Arch User Repository) packaging files for the Pacman Sync Utility.

## Package Variants

This PKGBUILD provides three package options:

### 1. `pacman-sync-utility` (Main Package)
- **Description**: Complete package with both client and server components
- **Use Case**: Single-machine setup or when you need both components
- **Dependencies**: Includes all client and server dependencies
- **Services**: Installs both systemd system service (server) and user service (client)

### 2. `pacman-sync-utility-client`
- **Description**: Client-only package
- **Use Case**: Client machines that connect to a remote server
- **Dependencies**: Only client-related dependencies (Qt6, aiohttp, etc.)
- **Services**: Installs only the systemd user service for the client
- **Conflicts**: Cannot be installed alongside the main package

### 3. `pacman-sync-utility-server`
- **Description**: Server-only package
- **Use Case**: Dedicated server machines
- **Dependencies**: Only server-related dependencies (FastAPI, uvicorn, etc.)
- **Services**: Installs only the systemd system service for the server
- **Conflicts**: Cannot be installed alongside the main package

## Installation

### Using an AUR Helper (Recommended)

```bash
# Install complete package
yay -S pacman-sync-utility

# Or install client-only
yay -S pacman-sync-utility-client

# Or install server-only
yay -S pacman-sync-utility-server
```

### Manual Installation

```bash
# Clone the AUR repository
git clone https://aur.archlinux.org/pacman-sync-utility.git
cd pacman-sync-utility

# Build and install
makepkg -si
```

## Post-Installation Setup

### For Server Component

1. **Enable and start the server service:**
   ```bash
   sudo systemctl enable --now pacman-sync-server
   ```

2. **Check service status:**
   ```bash
   sudo systemctl status pacman-sync-server
   ```

3. **View logs:**
   ```bash
   sudo journalctl -u pacman-sync-server -f
   ```

### For Client Component

1. **Enable and start the client service for your user:**
   ```bash
   systemctl --user enable --now pacman-sync-client
   ```

2. **Check service status:**
   ```bash
   systemctl --user status pacman-sync-client
   ```

3. **Launch GUI client manually:**
   ```bash
   pacman-sync-client
   ```

## Configuration

Configuration files are installed to `/etc/pacman-sync-utility/`:

- `server.conf` - Server configuration
- `client.conf` - Client configuration

These files are marked as backup files, so your customizations will be preserved during package updates.

## File Locations

- **Executables**: `/usr/bin/pacman-sync-{client,server,cli}`
- **Configuration**: `/etc/pacman-sync-utility/`
- **Data Directory**: `/var/lib/pacman-sync-utility/`
- **Log Directory**: `/var/log/pacman-sync-utility/`
- **Systemd Services**: 
  - System: `/usr/lib/systemd/system/pacman-sync-server.service`
  - User: `/usr/lib/systemd/user/pacman-sync-client.service`
- **Desktop Entry**: `/usr/share/applications/pacman-sync-utility.desktop`
- **Icons**: `/usr/share/icons/hicolor/*/apps/pacman-sync-utility.*`

## Dependencies

### Runtime Dependencies

**Client Package:**
- python (≥3.8)
- python-aiohttp
- python-pyqt6
- python-requests
- python-click
- python-psutil
- qt6-base

**Server Package:**
- python (≥3.8)
- python-fastapi
- python-uvicorn
- python-asyncpg
- python-pydantic
- python-jwt
- python-bcrypt
- python-click
- python-psutil

### Optional Dependencies

- `postgresql`: For production database backend (instead of SQLite)
- `waybar`: For status bar integration
- `python-psycopg2`: For PostgreSQL database support
- `systemd`: For service management

## Building from Source

If you need to modify the PKGBUILD or build from a different source:

1. **Update source URL and checksums in PKGBUILD**
2. **Generate new .SRCINFO:**
   ```bash
   makepkg --printsrcinfo > .SRCINFO
   ```
3. **Build package:**
   ```bash
   makepkg -s
   ```

## Troubleshooting

### Service Won't Start

Check the service logs:
```bash
# For server
sudo journalctl -u pacman-sync-server -n 50

# For client
journalctl --user -u pacman-sync-client -n 50
```

### Permission Issues

Ensure the pacman-sync user exists and has proper permissions:
```bash
sudo systemd-sysusers /usr/lib/sysusers.d/pacman-sync-utility.conf
sudo systemd-tmpfiles --create /usr/lib/tmpfiles.d/pacman-sync-utility.conf
```

### Database Issues

Reinitialize the database:
```bash
sudo -u pacman-sync /usr/bin/pacman-sync-server --init-db
```

### GUI Client Issues

Ensure you have a display server running and proper environment variables:
```bash
echo $DISPLAY
echo $QT_QPA_PLATFORM
```

## Contributing

To contribute to the AUR package:

1. Test the package thoroughly
2. Update version numbers and checksums
3. Regenerate .SRCINFO with `makepkg --printsrcinfo > .SRCINFO`
4. Submit changes to the AUR repository

## Support

- **Project Repository**: https://github.com/user/pacman-sync-utility
- **AUR Package**: https://aur.archlinux.org/packages/pacman-sync-utility
- **Issues**: Report packaging issues to the AUR comments or project repository