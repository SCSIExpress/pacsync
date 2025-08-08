# Installation Guide

This guide covers the complete installation process for the Pacman Sync Utility, including both server and client components.

## System Requirements

### Server Requirements
- **Operating System**: Linux (any distribution with Docker support)
- **Python**: 3.8 or higher
- **Database**: PostgreSQL 12+ (recommended) or SQLite (built-in)
- **Memory**: Minimum 512MB RAM, 1GB+ recommended
- **Storage**: 1GB+ for application and database
- **Network**: HTTP/HTTPS connectivity for client communication

### Client Requirements
- **Operating System**: Arch Linux or Arch-based distribution
- **Python**: 3.8 or higher
- **Qt**: Qt6 with Python bindings (PyQt6 or PySide6)
- **Pacman**: Standard Arch Linux package manager
- **Desktop Environment**: Any DE with system tray support
- **Network**: HTTP/HTTPS connectivity to server

## Installation Methods

### Method 1: Automated Installation (Recommended)

The automated installation script handles all dependencies and configuration:

```bash
# Download the repository
git clone https://github.com/your-org/pacman-sync-utility.git
cd pacman-sync-utility

# Make installation script executable
chmod +x install.sh

# Install server and client with systemd services
sudo ./install.sh --server --client --systemd

# Configure with interactive prompts
python3 setup.py configure --interactive

# Start services
python3 setup.py start --services server client
```

### Method 2: Manual Installation

#### Server Installation

1. **Install Python Dependencies**
   ```bash
   # Install system packages
   sudo pacman -S python python-pip postgresql-libs

   # Install Python packages
   pip install -r server-requirements.txt
   ```

2. **Database Setup**
   
   **Option A: PostgreSQL (Recommended for Production)**
   ```bash
   # Install PostgreSQL
   sudo pacman -S postgresql

   # Initialize database
   sudo -u postgres initdb -D /var/lib/postgres/data

   # Start PostgreSQL service
   sudo systemctl enable --now postgresql

   # Create database and user
   sudo -u postgres createuser -P pacman_sync
   sudo -u postgres createdb -O pacman_sync pacman_sync_db
   ```

   **Option B: SQLite (Development/Single User)**
   ```bash
   # SQLite is included with Python, no additional setup needed
   # Database file will be created automatically
   ```

3. **Server Configuration**
   ```bash
   # Create configuration directory
   sudo mkdir -p /etc/pacman-sync

   # Copy and customize server configuration
   sudo cp config/server.conf.template /etc/pacman-sync/server.conf
   sudo nano /etc/pacman-sync/server.conf
   ```

4. **Install Server Files**
   ```bash
   # Create application directory
   sudo mkdir -p /opt/pacman-sync

   # Copy server files
   sudo cp -r server/ shared/ /opt/pacman-sync/
   sudo chown -R root:root /opt/pacman-sync
   sudo chmod +x /opt/pacman-sync/server/main.py
   ```

5. **Create Systemd Service**
   ```bash
   # Copy service file
   sudo cp systemd/pacman-sync-server.service /etc/systemd/system/

   # Reload systemd and enable service
   sudo systemctl daemon-reload
   sudo systemctl enable pacman-sync-server
   ```

#### Client Installation

1. **Install Dependencies**
   ```bash
   # Install system packages
   sudo pacman -S python python-pip qt6-base python-pyqt6

   # Install Python packages
   pip install -r requirements.txt
   ```

2. **Client Configuration**
   ```bash
   # Create user configuration directory
   mkdir -p ~/.config/pacman-sync

   # Copy and customize client configuration
   cp config/client.conf.template ~/.config/pacman-sync/client.conf
   nano ~/.config/pacman-sync/client.conf
   ```

3. **Install Client Files**
   ```bash
   # Install to user directory
   mkdir -p ~/.local/share/pacman-sync
   cp -r client/ shared/ ~/.local/share/pacman-sync/

   # Make client executable
   chmod +x ~/.local/share/pacman-sync/client/main.py

   # Create desktop entry
   cp desktop/pacman-sync-client.desktop ~/.local/share/applications/
   ```

4. **Create User Systemd Service**
   ```bash
   # Create user systemd directory
   mkdir -p ~/.config/systemd/user

   # Copy service file
   cp systemd/pacman-sync-client.service ~/.config/systemd/user/

   # Enable user service
   systemctl --user daemon-reload
   systemctl --user enable pacman-sync-client
   ```

### Method 3: Docker Installation

#### Server-Only Docker Deployment

1. **Using Docker Compose (Recommended)**
   ```bash
   # Copy docker-compose configuration
   cp docker-compose.yml.example docker-compose.yml
   nano docker-compose.yml  # Customize settings

   # Start services
   docker-compose up -d

   # Check status
   docker-compose ps
   ```

2. **Manual Docker Deployment**
   ```bash
   # Build image
   docker build -t pacman-sync-server .

   # Run with PostgreSQL
   docker run -d \
     --name pacman-sync-server \
     -p 8080:8080 \
     -e DATABASE_TYPE=postgresql \
     -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
     -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
     -v pacman-sync-data:/app/data \
     pacman-sync-server

   # Run with internal database
   docker run -d \
     --name pacman-sync-server \
     -p 8080:8080 \
     -e DATABASE_TYPE=internal \
     -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
     -v pacman-sync-data:/app/data \
     pacman-sync-server
   ```

## Post-Installation Setup

### 1. Server Initialization

```bash
# Start the server
sudo systemctl start pacman-sync-server

# Check server status
sudo systemctl status pacman-sync-server

# Verify server is responding
curl http://localhost:8080/health/live

# Check server logs
sudo journalctl -u pacman-sync-server -f
```

### 2. Client Registration

```bash
# Start the client
systemctl --user start pacman-sync-client

# Check client status
systemctl --user status pacman-sync-client

# Verify client registration
python -m client.main --status

# Check client logs
journalctl --user -u pacman-sync-client -f
```

### 3. Web UI Access

1. Open your web browser
2. Navigate to `http://your-server:8080`
3. Create your first package pool
4. Add endpoints to the pool

### 4. Validation

Run the validation script to ensure everything is working:

```bash
# Validate complete installation
python3 scripts/validate-deployment.py --components all

# Test client-server communication
python3 scripts/integrate-components.py --test-communication

# Run basic functionality tests
python3 -m pytest tests/test_basic_functionality.py -v
```

## Configuration Files

### Server Configuration (`/etc/pacman-sync/server.conf`)

```ini
[database]
type = postgresql
url = postgresql://pacman_sync:password@localhost:5432/pacman_sync_db

[server]
host = 0.0.0.0
port = 8080
debug = false

[security]
jwt_secret_key = your-secret-key-here
api_rate_limit = 100

[features]
enable_repository_analysis = true
auto_cleanup_old_states = true
max_state_history = 50
```

### Client Configuration (`~/.config/pacman-sync/client.conf`)

```ini
[server]
url = http://your-server:8080
api_key = your-api-key

[client]
endpoint_name = my-desktop
pool_id = default-pool
auto_sync = false

[ui]
show_notifications = true
minimize_to_tray = true
update_interval = 300
theme = system

[pacman]
config_path = /etc/pacman.conf
cache_dir = /var/cache/pacman/pkg
```

## Troubleshooting Installation

### Common Issues

1. **Server won't start**
   ```bash
   # Check configuration
   sudo python3 -m server.main --check-config

   # Check database connection
   sudo python3 -m server.database.connection --test

   # Check logs
   sudo journalctl -u pacman-sync-server --no-pager
   ```

2. **Client can't connect to server**
   ```bash
   # Test network connectivity
   curl http://your-server:8080/health/live

   # Check client configuration
   python3 -m client.main --check-config

   # Test API authentication
   python3 -m client.api_client --test-auth
   ```

3. **System tray icon not appearing**
   ```bash
   # Check desktop environment support
   python3 -m client.qt.application --test-tray

   # Check Qt installation
   python3 -c "from PyQt6.QtWidgets import QApplication, QSystemTrayIcon; print('Qt OK')"

   # Run client in debug mode
   python3 -m client.main --debug --no-tray
   ```

### Getting Help

If you encounter issues not covered here:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review server and client logs
3. Run the diagnostic script: `python3 scripts/diagnose-issues.py`
4. Create an issue on GitHub with diagnostic output

## Next Steps

After successful installation:

1. Read the [Configuration Guide](configuration.md) for advanced settings
2. Follow the [Web UI Guide](web-ui-guide.md) to set up your first pool
3. Check the [Desktop Client Guide](desktop-client-guide.md) for daily usage
4. Set up [WayBar Integration](waybar_integration.md) if using Wayland

## Uninstallation

To completely remove the Pacman Sync Utility:

```bash
# Stop services
sudo systemctl stop pacman-sync-server
systemctl --user stop pacman-sync-client

# Disable services
sudo systemctl disable pacman-sync-server
systemctl --user disable pacman-sync-client

# Remove files
sudo rm -rf /opt/pacman-sync
sudo rm -rf /etc/pacman-sync
rm -rf ~/.local/share/pacman-sync
rm -rf ~/.config/pacman-sync

# Remove systemd services
sudo rm /etc/systemd/system/pacman-sync-server.service
rm ~/.config/systemd/user/pacman-sync-client.service

# Reload systemd
sudo systemctl daemon-reload
systemctl --user daemon-reload

# Remove database (optional)
sudo -u postgres dropdb pacman_sync_db
sudo -u postgres dropuser pacman_sync
```